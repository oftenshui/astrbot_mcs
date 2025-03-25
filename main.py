import random
import asyncio
import os
import json
import datetime
import aiohttp
import urllib.parse
import logging
from PIL import Image as PILImage
from PIL import ImageDraw as PILImageDraw
from PIL import ImageFont as PILImageFont
from astrbot.api.all import AstrMessageEvent, CommandResult, Context, Image, Plain
import astrbot.api.event.filter as filter
from astrbot.api.star import register, Star

logger = logging.getLogger("astrbot")


@register("astrbot_plugin_essential", "Soulter", "", "", "")
class Main(Star):
    def __init__(self, context: Context) -> None:
        super().__init__(context)
        self.PLUGIN_NAME = "astrbot_plugin_essential"
        PLUGIN_NAME = self.PLUGIN_NAME
        path = os.path.abspath(os.path.dirname(__file__))
        self.mc_html_tmpl = open(
            path + "/templates/mcs.html", "r", encoding="utf-8"
        ).read()
        self.what_to_eat_data: list = json.loads(
            open(path + "/resources/food.json", "r", encoding="utf-8").read()
        )["data"]

        if not os.path.exists(f"data/{PLUGIN_NAME}_data.json"):
            with open(f"data/{PLUGIN_NAME}_data.json", "w", encoding="utf-8") as f:
                f.write(json.dumps({}, ensure_ascii=False, indent=2))
        with open(f"data/{PLUGIN_NAME}_data.json", "r", encoding="utf-8") as f:
            self.data = json.loads(f.read())
        self.good_morning_data = self.data.get("good_morning", {})

        # moe
        self.moe_urls = [
            "https://t.mwm.moe/pc/",
            "https://t.mwm.moe/mp",
            "https://www.loliapi.com/acg/",
            "https://www.loliapi.com/acg/pc/",
        ]

        self.search_anmime_demand_users = {}

    def time_convert(self, t):
        m, s = divmod(t, 60)
        return f"{int(m)}分{int(s)}秒"

    @filter.event_message_type(filter.EventMessageType.ALL)
    async def handle_search_anime(self, message: AstrMessageEvent):
        """检查是否有搜番请求"""
        sender = message.get_sender_id()
        if sender in self.search_anmime_demand_users:
            message_obj = message.message_obj
            url = "https://api.trace.moe/search?anilistInfo&url="
            image_obj = None
            for i in message_obj.message:
                if isinstance(i, Image):
                    image_obj = i
                    break
            try:
                try:
                    # 需要经过url encode
                    image_url = urllib.parse.quote(image_obj.url)
                    url += image_url
                except BaseException as _:
                    if sender in self.search_anmime_demand_users:
                        del self.search_anmime_demand_users[sender]
                    return CommandResult().error(
                        f"发现不受本插件支持的图片数据：{type(image_obj)}，插件无法解析。"
                    )

                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as resp:
                        if resp.status != 200:
                            if sender in self.search_anmime_demand_users:
                                del self.search_anmime_demand_users[sender]
                            return CommandResult().error("请求失败")
                        data = await resp.json()

                if data["result"] and len(data["result"]) > 0:
                    # 番剧时间转换为x分x秒
                    data["result"][0]["from"] = self.time_convert(
                        data["result"][0]["from"]
                    )
                    data["result"][0]["to"] = self.time_convert(data["result"][0]["to"])

                    warn = ""
                    if float(data["result"][0]["similarity"]) < 0.8:
                        warn = "相似度过低，可能不是同一番剧。建议：相同尺寸大小的截图; 去除四周的黑边\n\n"
                    if sender in self.search_anmime_demand_users:
                        del self.search_anmime_demand_users[sender]
                    return CommandResult(
                        chain=[
                            Plain(
                                f"{warn}番名: {data['result'][0]['anilist']['title']['native']}\n相似度: {data['result'][0]['similarity']}\n剧集: 第{data['result'][0]['episode']}集\n时间: {data['result'][0]['from']} - {data['result'][0]['to']}\n精准空降截图:"
                            ),
                            Image.fromURL(data["result"][0]["image"]),
                        ],
                        use_t2i_=False,
                    )
                else:
                    if sender in self.search_anmime_demand_users:
                        del self.search_anmime_demand_users[sender]
                    return CommandResult(True, False, [Plain("没有找到番剧")], "sf")
            except Exception as e:
                raise e

    @filter.command("喜报")
    async def congrats(self, message: AstrMessageEvent):
        """喜报生成器"""
        msg = message.message_str.replace("喜报", "").strip()
        for i in range(20, len(msg), 20):
            msg = msg[:i] + "\n" + msg[i:]

        path = os.path.abspath(os.path.dirname(__file__))
        bg = path + "/congrats.jpg"
        img = PILImage.open(bg)
        draw = PILImageDraw.Draw(img)
        font = PILImageFont.truetype(path + "/simhei.ttf", 65)

        # Calculate the width and height of the text
        text_width, text_height = draw.textbbox((0, 0), msg, font=font)[2:4]

        # Calculate the starting position of the text to center it.
        x = (img.size[0] - text_width) / 2
        y = (img.size[1] - text_height) / 2

        draw.text(
            (x, y),
            msg,
            font=font,
            fill=(255, 0, 0),
            stroke_width=3,
            stroke_fill=(255, 255, 0),
        )

        img.save("congrats_result.jpg")
        return CommandResult().file_image("congrats_result.jpg")

    @filter.command("悲报")
    async def uncongrats(self, message: AstrMessageEvent):
        """悲报生成器"""
        msg = message.message_str.replace("悲报", "").strip()
        for i in range(20, len(msg), 20):
            msg = msg[:i] + "\n" + msg[i:]

        path = os.path.abspath(os.path.dirname(__file__))
        bg = path + "/uncongrats.jpg"
        img = PILImage.open(bg)
        draw = PILImageDraw.Draw(img)
        font = PILImageFont.truetype(path + "/simhei.ttf", 65)

        # Calculate the width and height of the text
        text_width, text_height = draw.textbbox((0, 0), msg, font=font)[2:4]

        # Calculate the starting position of the text to center it.
        x = (img.size[0] - text_width) / 2
        y = (img.size[1] - text_height) / 2

        draw.text(
            (x, y),
            msg,
            font=font,
            fill=(0, 0, 0),
            stroke_width=3,
            stroke_fill=(255, 255, 255),
        )

        img.save("uncongrats_result.jpg")
        return CommandResult().file_image("uncongrats_result.jpg")

    @filter.command("moe")
    async def get_moe(self, message: AstrMessageEvent):
        """随机动漫图片"""
        shuffle = random.sample(self.moe_urls, len(self.moe_urls))
        for url in shuffle:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as resp:
                        if resp.status != 200:
                            return CommandResult().error(f"获取图片失败: {resp.status}")
                        data = await resp.read()
                        break
            except Exception as e:
                logger.error(f"从 {url} 获取图片失败: {e}。正在尝试下一个API。")
                continue
        # 保存图片到本地
        try:
            with open("moe.jpg", "wb") as f:
                f.write(data)
            return CommandResult().file_image("moe.jpg")

        except Exception as e:
            return CommandResult().error(f"保存图片失败: {e}")

    @filter.command("搜番")
    async def get_search_anime(self, message: AstrMessageEvent):
        """以图搜番"""
        sender = message.get_sender_id()
        if sender in self.search_anmime_demand_users:
            yield message.plain_result("正在等你发图喵，请不要重复发送")
        self.search_anmime_demand_users[sender] = False
        yield message.plain_result("请在 30 喵内发送一张图片让我识别喵")
        await asyncio.sleep(30)
        if sender in self.search_anmime_demand_users:
            if self.search_anmime_demand_users[sender]:
                del self.search_anmime_demand_users[sender]
                return
            del self.search_anmime_demand_users[sender]
            yield message.plain_result("🧐你没有发送图片，搜番请求已取消了喵")

@filter.command("mcs")
async def mcs(self, message: AstrMessageEvent):
    """查mc服务器"""
    message_str = message.message_str
    if message_str == "mcs":
        return CommandResult().error("查 Minecraft 服务器。格式: /mcs [服务器地址]")

    ip = message_str.replace("mcs", "").strip()
    url = f"https://sr-api.sfirew.com/server/{ip}"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                return CommandResult().error("请求失败")
            data = await resp.json()
            logger.info(f"获取到 {ip} 的服务器信息。")

    # 处理 MOTD
    motd = data.get("motd", {}).get("cleaned", "查询失败")

    # 处理玩家信息
    players = "查询失败"
    online_players = []
    
    if "players" in data:
        players = f"{data['players']['online']}/{data['players']['max']}"
        online_players = [p["name"] for p in data["players"].get("sample", [])]

    # 兼容 info.raw 里的玩家信息
    if not online_players and "info" in data:
        online_players = [p["name"] for p in data["info"].get("raw", [])]

    # 处理版本信息
    version = data.get("version", {}).get("raw", "查询失败")

    # 服务器状态
    status = "🟢" if data.get("online", False) else "🔴"

    # 处理 Ping 延迟
    ping = data.get("ping", "未知")

    # 生成在线玩家列表
    name_list_str = "\n".join(online_players) if online_players else "无玩家在线"

    # 构造返回文本
    result_text = (
        "【查询结果】\n"
        f"状态: {status}\n"
        f"服务器IP: {ip}\n"
        f"版本: {version}\n"
        f"延迟: {ping}ms\n"
        f"MOTD: {motd}\n"
        f"玩家人数: {players}\n"
        f"在线玩家: \n{name_list_str}"
    )

    return CommandResult().message(result_text).use_t2i(False)

# 确保这里有空行

@filter.command("一言")
async def hitokoto(self, message: AstrMessageEvent):
    """来一条一言"""
    url = "https://v1.hitokoto.cn"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                return CommandResult().error("请求失败")
            data = await resp.json()
    return CommandResult().message(data["hitokoto"] + " —— " + data["from"])

async def save_what_eat_data(self):
    path = os.path.abspath(os.path.dirname(__file__))
    food_json_path = os.path.join(path, "resources", "food.json")
    with open(food_json_path, "w", encoding="utf-8") as f:
        json.dump({"data": self.what_to_eat_data}, f, ensure_ascii=False, indent=2)

class BotCommands:
    def __init__(self):
        self.what_to_eat_data: List[str] = []
        self.good_morning_data = {}
        self.PLUGIN_NAME = "bot_plugin"

    async def save_what_eat_data(self):
        """保存食物列表"""
        with open("data/what_to_eat.json", "w", encoding="utf-8") as f:
            json.dump(self.what_to_eat_data, f, ensure_ascii=False, indent=2)

    @filter.command("今天吃什么")
    async def what_to_eat(self, message: AstrMessageEvent):
        """今天吃什么"""
        cmd, *items = message.message_str.split(" ")

        if cmd == "添加":
            if not items:
                return CommandResult().error("格式：今天吃什么 添加 [食物1] [食物2] ...")
            self.what_to_eat_data.extend(items)
            await self.save_what_eat_data()
            return CommandResult().message("添加成功")

        if cmd == "删除":
            if not items:
                return CommandResult().error("格式：今天吃什么 删除 [食物1] [食物2] ...")
            self.what_to_eat_data = [item for item in self.what_to_eat_data if item not in items]
            await self.save_what_eat_data()
            return CommandResult().message("删除成功")

        if self.what_to_eat_data:
            return CommandResult().message(f"今天吃 {random.choice(self.what_to_eat_data)}！")
        return CommandResult().message("食物列表为空，请先添加食物")

    @filter.command("喜加一")
    async def epic_free_game(self, message: AstrMessageEvent):
        """获取EPIC商店的免费游戏"""
        url = "https://store-site-backend-static-ipv4.ak.epicgames.com/freeGamesPromotions"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    return CommandResult().error("请求失败")
                data = await resp.json()

        games = []
        upcoming = []

        for game in data.get("data", {}).get("Catalog", {}).get("searchStore", {}).get("elements", []):
            title = game.get("title", "未知")
            price_info = game.get("price", {}).get("totalPrice", {}).get("fmtPrice", {})
            original_price, discount_price = price_info.get("originalPrice", "未知"), price_info.get("discountPrice", "未知")

            promotions = game.get("promotions", {})
            active_promotions = promotions.get("promotionalOffers", [])
            upcoming_promotions = promotions.get("upcomingPromotionalOffers", [])

            if active_promotions:
                promotion = active_promotions[0]["promotionalOffers"][0]
            elif upcoming_promotions:
                promotion = upcoming_promotions[0]["promotionalOffers"][0]
            else:
                continue

            discount = float(promotion["discountSetting"]["discountPercentage"])
            if discount != 0:
                continue

            start = datetime.datetime.strptime(promotion["startDate"], "%Y-%m-%dT%H:%M:%S.%fZ") + datetime.timedelta(hours=8)
            end = datetime.datetime.strptime(promotion["endDate"], "%Y-%m-%dT%H:%M:%S.%fZ") + datetime.timedelta(hours=8)

            game_info = f"【{title}】\n原价: {original_price} | 现价: {discount_price}\n活动时间: {start.strftime('%Y-%m-%d %H:%M')} - {end.strftime('%Y-%m-%d %H:%M')}"
            (games if active_promotions else upcoming).append(game_info)

        result = "【EPIC 喜加一】\n" + "\n\n".join(games) + "\n\n【即将免费】\n" + "\n\n".join(upcoming)
        return CommandResult().message(result if games else "暂无免费游戏").use_t2i(False)

    @filter.regex(r"^(早安|晚安)")
    async def good_morning(self, message: AstrMessageEvent):
        """记录早晚安时间"""
        umo_id, user = message.unified_msg_origin, message.message_obj.sender
        user_id, user_name = user.user_id, user.nickname
        curr_time = datetime.datetime.utcnow() + datetime.timedelta(hours=8)
        curr_time_str = curr_time.strftime("%Y-%m-%d %H:%M:%S")
        is_night = "晚安" in message.message_str

        user_data = self.good_morning_data.setdefault(umo_id, {}).setdefault(user_id, {"daily": {"morning_time": "", "night_time": ""}})
        if is_night:
            user_data["daily"]["night_time"] = curr_time_str
            user_data["daily"]["morning_time"] = ""
        else:
            user_data["daily"]["morning_time"] = curr_time_str

        # 统计今天睡觉的人数
        curr_day_sleeping = sum(
            1 for v in self.good_morning_data[umo_id].values()
            if v["daily"]["night_time"] and not v["daily"]["morning_time"] and
            datetime.datetime.strptime(v["daily"]["night_time"], "%Y-%m-%d %H:%M:%S").day == curr_time.day
        )

        # 计算睡眠时间
        if not is_night and user_data["daily"]["night_time"]:
            night_time = datetime.datetime.strptime(user_data["daily"]["night_time"], "%Y-%m-%d %H:%M:%S")
            sleep_duration = (curr_time - night_time).total_seconds()
            sleep_duration_human = f"{int(sleep_duration / 3600)}小时{int((sleep_duration % 3600) / 60)}分"
            return CommandResult().message(f"早安喵，{user_name}！\n现在是 {curr_time_str}，昨晚你睡了 {sleep_duration_human}。").use_t2i(False)

        return CommandResult().message(f"晚安喵，{user_name}！\n现在是 {curr_time_str}，你是本群今天第 {curr_day_sleeping} 个睡觉的。").use_t2i(False)
