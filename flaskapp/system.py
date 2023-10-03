import bcrypt
import traceback
from config import user_data


def hash_password(password):
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
    return salt, hashed_password


def verify_password(password, stored_salt, stored_hash):
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), stored_salt)
    return hashed_password == stored_hash


def login(username, password):
    try:
        result = user_data.find_one({"username": username})
        print(result)
        if result is None:
            code = 100
        else:
            if verify_password(password, result['salt'], result['hashed_password']):
                code = 300
            else:
                code = 100
    except Exception:
        print(traceback.print_exc())
        code = 400
    return code


def register(username, password):
    try:
        result = user_data.find_one({"username": username})
        if result:
            code = 200
        else:
            salt, hashed_password = hash_password(password)
            user_data.insert_one(
                {"username": username, "salt": salt, "hashed_password": hashed_password})
            code = 300
    except Exception:
        print(traceback.print_exc())
        code = 400
    return code
