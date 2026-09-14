
# 全局字典 用来存放技师的忙碌时间段信息，
from enum import Enum
busy_periods_dict = {}  # { technician_id: [ {"start": "...", "end": "..."} ] }
                        #  键为技师ID，值为一个列表，列表中每个元素是一个字典，包含开始时间和结束时间

# 定义系统状态 共4个状态 分类、预约中、咨询中、其他
class StateEnum(Enum):
    CLASSIFY = "classify"
    APPOINTMENT = "appointment"
    CONSULT = "consult"
    OTHER = "other"

# 共享状态容器 只有一个属性value 初始值为CLASSIFY 其他状态通过修改value属性来改变 会被StateManager监控到变化
class SharedState:
    def __init__(self):
        self.value = StateEnum.CLASSIFY
