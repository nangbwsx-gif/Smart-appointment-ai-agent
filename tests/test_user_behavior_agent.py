"""
UserBehaviorAgent 功能测试

对齐 agents/user_behavior_agent.py 的真实接口：
- 行为记录：BehaviorRecorder.record_behavior(action_type, action_data)
- 偏好分析：PatternAnalyzer.analyze_user_preferences(user_id)
- 行为模式：UserBehaviorService.analyze_user_patterns(user_id)
- 统计信息：BehaviorRecorder.get_behavior_statistics(days_back)
- 回访消息：UserBehaviorAgent.generate_reminder_message(user_id)
- 偏好存储：PreferenceManager.update_*_preference / get_user_preferences
"""

import pytest
import uuid
from agents.user_behavior_agent import UserBehaviorAgent
from datetime import datetime, timedelta


def _record(agent, user_id, action_type="appointment", action_data=None, technician_id=None):
    """按用户写入一条行为，便于测试之间互不干扰"""
    return agent.user_behavior_service.record_behavior(
        user_id=user_id,
        action_type=action_type,
        action_data=action_data if action_data is not None else {},
        technician_id=technician_id,
        session_id="test_session",
    )


class TestUserBehaviorAgentCoreFeatures:
    """测试用户行为代理核心功能"""

    def test_should_record_user_behavior_correctly(self):
        """应该正确记录用户行为，并可按用户检索"""
        agent = UserBehaviorAgent()

        result = agent.behavior_recorder.record_behavior(
            action_type="consultation",
            action_data={"query": "全身推拿多少钱"},
        )
        assert result is not None, "行为记录应该返回结果"

        behaviors = agent.user_behavior_service.get_user_behaviors(
            user_id="default_user", action_type="consultation"
        )
        assert behaviors, "应该能检索到刚记录的行为"

        latest = behaviors[0]
        assert latest["action_type"] == "consultation"
        assert latest["action_data"]["query"] == "全身推拿多少钱"

    def test_should_analyze_user_preferences_correctly(self):
        """应该基于预约历史分析出偏好服务与时长"""
        agent = UserBehaviorAgent()
        user_id = f"test_prefs_user_{uuid.uuid4().hex[:8]}"

        _record(agent, user_id, action_data={"project": "肩颈按摩", "duration": 60})
        _record(agent, user_id, action_data={"project": "肩颈按摩", "duration": 60})
        _record(agent, user_id, action_data={"project": "足疗", "duration": 30})

        preferences = agent.pattern_analyzer.analyze_user_preferences(user_id)

        assert preferences is not None, "应该返回偏好分析结果"
        assert preferences["favorite_service"] == "肩颈按摩", \
            f"应该识别肩颈按摩为偏好服务，但得到：{preferences['favorite_service']}"
        assert preferences["favorite_duration"] == 60, \
            f"应该识别60分钟为偏好时长，但得到：{preferences['favorite_duration']}"
        assert preferences["total_appointments"] >= 3

    def test_should_identify_behavior_patterns(self):
        """应该识别出预约频率等行为模式"""
        agent = UserBehaviorAgent()
        user_id = f"test_pattern_user_{uuid.uuid4().hex[:8]}"

        for i in range(3):
            start = datetime.now() - timedelta(days=10 + i * 2)
            _record(agent, user_id, action_data={"start_time": start.isoformat(), "duration": 60})

        patterns = agent.user_behavior_service.analyze_user_patterns(user_id)

        assert patterns is not None, "应该返回模式分析结果"
        assert patterns["total_appointments"] == 3
        assert "frequency_analysis" in patterns
        assert patterns["frequency_analysis"]["frequency"] in (
            "no_appointments", "single_appointment", "insufficient_data",
            "very_frequent", "frequent", "regular", "occasional",
        )

    def test_should_provide_behavior_insights(self):
        """应该生成有意义的回访消息"""
        agent = UserBehaviorAgent()
        user_id = f"test_insight_user_{uuid.uuid4().hex[:8]}"

        _record(agent, user_id, action_data={"project": "全身按摩", "duration": 60}, technician_id=1)

        message = agent.generate_reminder_message(user_id)

        assert message, "应该返回回访消息"
        assert any(term in message for term in ("预约", "按摩", "技师")), \
            f"消息应该包含有意义的分析内容：{message}"

    def test_should_manage_user_preferences_storage(self):
        """应该正确管理用户偏好存储"""
        agent = UserBehaviorAgent()

        agent.preference_manager.update_service_preference("测试偏好项目")
        agent.preference_manager.update_duration_preference("45")

        preferences = agent.preference_manager.get_user_preferences()

        assert isinstance(preferences, dict), f"偏好应该是字典结构：{type(preferences)}"
        assert "测试偏好项目" in list(preferences.values()), f"应该存下服务偏好：{preferences}"
        assert "45" in list(preferences.values()), f"应该存下时长偏好：{preferences}"

    def test_should_handle_data_aggregation(self):
        """应该返回行为统计信息"""
        agent = UserBehaviorAgent()
        user_id = f"test_agg_user_{uuid.uuid4().hex[:8]}"
        _record(agent, user_id, action_data={"project": "按摩", "duration": 60})

        stats = agent.behavior_recorder.get_behavior_statistics(days_back=30)

        assert isinstance(stats, dict), "统计结果应该是字典"
        assert "total_behaviors" in stats
        assert stats["total_behaviors"] >= 1

    def test_should_handle_privacy_and_data_cleanup(self):
        """旧数据清理接口应可用且返回清理数量"""
        agent = UserBehaviorAgent()
        user_id = f"test_cleanup_user_{uuid.uuid4().hex[:8]}"
        _record(agent, user_id, action_data={"phone_number": "13800138000", "real_name": "张三"})

        deleted_count = agent.behavior_recorder.delete_old_behaviors(days_to_keep=365)

        assert isinstance(deleted_count, int), "应该返回清理数量"

        # 敏感字段只存在于行为明细中，不应出现在偏好汇总里
        preferences = agent.preference_manager.get_user_preferences()
        assert "13800138000" not in str(preferences)
        assert "张三" not in str(preferences)


class TestUserBehaviorAgentEdgeCases:
    """测试边界情况"""

    def test_should_handle_new_user_with_no_history(self):
        """新用户没有历史记录时不应报错"""
        agent = UserBehaviorAgent()
        new_user_id = "brand_new_user"

        preferences = agent.pattern_analyzer.analyze_user_preferences(new_user_id)
        assert preferences is None or preferences == {}, "新用户偏好分析不应该出错"

        message = agent.generate_reminder_message(new_user_id)
        assert message, "新用户也应该得到默认回访消息"

    def test_should_handle_invalid_behavior_data(self):
        """无效数据不应导致崩溃"""
        agent = UserBehaviorAgent()

        invalid_data_cases = [
            ("", None),
            (None, None),
            ("appointment", "not-a-dict"),
        ]

        for action_type, action_data in invalid_data_cases:
            try:
                result = agent.behavior_recorder.record_behavior(
                    action_type=action_type, action_data=action_data
                )
            except (ValueError, TypeError, KeyError):
                continue
            assert result is None or isinstance(result, int), \
                f"无效数据应返回 None 或记录ID：{result}"
