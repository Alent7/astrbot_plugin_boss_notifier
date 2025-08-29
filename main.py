import json
from datetime import datetime
from astrbot.api.event import filter, AstrMessageEvent, MessageChain
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
import astrbot.api.message_components as Comp
import threading
import asyncio
from astrbot.api.star import StarTools

# 线程锁
LOCK = threading.Lock()

class BossData:
    """Boss 数据管理，包含订阅列表和头目信息"""
    def __init__(self):
        # 使用 StarTools 获取插件专属数据目录
        self.data_dir = StarTools.get_data_dir("astrbot_plugin_boss_notifier")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.data_file = self.data_dir / "boss_data.json"
        self.data = {"subscriptions": [], "boss": {}}
        self.load_data()

    def load_data(self):
        """从文件加载数据"""
        if self.data_file.exists():
            try:
                with open(self.data_file, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
                logger.info("Boss 数据加载成功")
            except Exception as e:
                logger.warning(f"Boss 数据加载失败: {e}")
                self.data = {"subscriptions": [], "boss": {}}

    def save_data(self):
        """保存数据到文件"""
        try:
            with LOCK:
                with open(self.data_file, "w", encoding="utf-8") as f:
                    json.dump(self.data, f, ensure_ascii=False, indent=2)
            logger.info("Boss 数据保存成功")
        except Exception as e:
            logger.error(f"Boss 数据保存失败: {e}")

    def add_subscription(self, user_id):
        user_id = str(user_id)
        if user_id not in self.data["subscriptions"]:
            self.data["subscriptions"].append(user_id)
            self.save_data()

    def remove_subscription(self, user_id):
        user_id = str(user_id)
        if user_id in self.data["subscriptions"]:
            self.data["subscriptions"].remove(user_id)
            self.save_data()

    def update_boss(self, place, name, iv, nature, feature, time_str=None):
        if not time_str:
            time_str = datetime.now().strftime("%Y/%m/%d-%H:%M")
        self.data["boss"] = {
            "place": place,
            "name": name,
            "iv": iv,
            "nature": nature,
            "feature": feature,
            "time": time_str,
        }
        self.save_data()

    def format_boss_md(self):
        if not self.data["boss"]:
            return "当前没有记录头目信息。"
        b = self.data["boss"]
        return (
            f"头目刷新提醒\n"
            f"- 时间：{b.get('time','')}\n"
            f"- 地点：{b.get('place','')}\n"
            f"- 精灵：{b.get('name','')}\n"
            f"- 个体：{b.get('iv','')}\n"
            f"- 性格：{b.get('nature','')}\n"
            f"- 特性：{b.get('feature','')}\n"
        )

# 全局实例
boss_data = BossData()


@register("astrbot_plugin_boss_notifier", "Alent7", "头目刷新提醒插件", "1.0.0", "https://github.com/Alent7/astrbot_plugin_boss_notifier")
class BossNotifier(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    @filter.command("订阅头目")
    async def subscribe(self, event: AstrMessageEvent):
        """
        /订阅头目 ：订阅当前QQ号
        """

        target_qq = str(event.get_sender_id())
        boss_data.add_subscription(target_qq)

        chain = [
            Comp.At(qq=target_qq),
            Comp.Plain("\n\n已成功订阅头目提醒")
        ]
        await self.context.send_message(event.unified_msg_origin, MessageChain(chain))

    @filter.command("取消订阅")
    async def unsubscribe(self, event: AstrMessageEvent):
        """
        /取消订阅 ：取消订阅当前QQ号
        """

        target_qq = str(event.get_sender_id())
        boss_data.remove_subscription(target_qq)

        chain = [
            Comp.At(qq=target_qq),
            Comp.Plain("\n\n已取消订阅头目提醒")
        ]
        await self.context.send_message(event.unified_msg_origin, MessageChain(chain))

    @filter.command("更新头目")
    async def update_boss(self, event: AstrMessageEvent, place: str, name: str, iv: str, nature: str, feature: str, time_str: str = None):
        """/更新头目：地点 精灵 个体 性格 特性 [时间可选]"""
        boss_data.update_boss(place, name, iv, nature, feature, time_str)
        yield event.plain_result("头目信息已更新")

    @filter.command("订阅列表")
    async def list_subscriptions(self, event: AstrMessageEvent):
        """/订阅列表：查询当前订阅用户"""
        if not boss_data.data["subscriptions"]:
            yield event.plain_result("当前没有订阅用户")
            return
        msg = "当前订阅用户:\n" + " ".join([f"@{uid}" for uid in boss_data.data["subscriptions"]])
        yield event.plain_result(msg)

    @filter.command("头目来了")
    async def notify_boss(self, event: AstrMessageEvent):
        """/头目来了：提醒所有订阅者"""
        if not boss_data.data["boss"]:
            yield event.plain_result("当前没有记录头目信息。")
            return

        at_chain = [Comp.At(qq=uid) for uid in boss_data.data["subscriptions"]]
        boss_info = boss_data.format_boss_md()
        msg_chain = MessageChain(at_chain + [Comp.Plain("\n\n" + boss_info)])
        await self.context.send_message(event.unified_msg_origin, msg_chain)

        yield event.plain_result("已通知所有订阅用户")

    @filter.command("头目")
    async def show_boss(self, event: AstrMessageEvent):
        """显示当前头目信息和指令用法"""
        md = boss_data.format_boss_md()
        usage = (
            "指令用法:\n"
            "/头目 （查询头目指令）\n"
            "/订阅头目 （订阅当前QQ号）\n"
            "/取消订阅 （取消当前QQ号）\n"
            "/更新头目：地点 精灵 个体 性格 特性 [时间可选]\n"
            "/订阅列表 （查询订阅列表）\n"
            "/头目来了 （提醒所有订阅者）\n\n"
            "更新头目例子：\n/更新头目 第1星系-火山3层 赤西西比 29 孤独 圣灵 2025/08/29-10:00"
        )
        yield event.plain_result(md + "\n\n" + usage)
