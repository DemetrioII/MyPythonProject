from pydantic import BaseModel  
class VkCallbackParams(BaseModel):
    code: int
    state: str
    device_id: int
