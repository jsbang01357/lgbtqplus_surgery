import asyncio
from app.security import verify_account_password, account_login_password, _verify_hash
pwd = account_login_password()
print(f"STORED_PWD: {pwd}")
print(f"VERIFY_RESULT: {verify_account_password('cbd_07079')}")
