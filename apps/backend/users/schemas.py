from datetime import datetime,timezone
from typing import Literal

from pydantic import BaseModel,EmailStr,ConfigDict,Field

class userCreate(BaseModel):
    username: str = Field(
        min_length=2,
        max_length=50,
        examples=["Kavindu"]
    )
    email: EmailStr = Field(
        examples=["kkpremarathna@gmail.com"]
    )
    password: str = Field(
        min_length=8,
        max_length=128,
        examples=["SecurePassword123!"],
    )
    
class userResponse(BaseModel):
    user_id:int
    username:str
    email:EmailStr
    role:Literal["ADMIN","CUSTOMER"]
    created_at:datetime
    
    model_config = ConfigDict(from_attributes=True)