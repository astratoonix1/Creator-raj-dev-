import datetime as dt
import motor.motor_asyncio
from config import DATABASE_URI, DATABASE_NAME


def now():
    return dt.datetime.utcnow()


class DB:
    def __init__(self):
        c = motor.motor_asyncio.AsyncIOMotorClient(DATABASE_URI)
        d = c[DATABASE_NAME]
        self.db = d
        self.users = d.users            # {id, name, ban:{...}, v1,v2,v3, trial}
        self.chats = d.chats            # groups
        self.premium = d.premium        # {id, expiry_time}
        self.contents = d.contents      # {_id:'m123', title, items:[msg_id], added}
        self.demand = d.demand          # {_id:'m123', title, count, has_content}
        self.searches = d.searches      # {_id:'query', count}
        self.tokens = d.tokens          # verify tokens
        self.codes = d.codes            # redeem codes
        self.joinreq = d.joinreq
        self.settings = d.settings      # {_id:'bot', ...}
        self.requests = d.requests
        self.refer = d.refer            # {user_id, points}
        self.referred = d.referred      # {user_id} jo kisi ke refer se aa chuke
        self.updates = d.movie_updates  # {_id: key} notification dedupe
        self.conns = d.connections      # {user_id, groups:[...]}

    # ---------- users ----------
    async def add_user(self, uid, name):
        if not await self.users.find_one({"id": uid}):
            await self.users.insert_one({"id": uid, "name": name, "ban": False, "reason": ""})
            return True
        return False

    async def is_user_exist(self, uid):
        return bool(await self.users.find_one({"id": uid}))

    async def get_user(self, uid):
        return await self.users.find_one({"id": uid}) or {}

    async def set_user(self, uid, **kw):
        await self.users.update_one({"id": uid}, {"$set": kw}, upsert=True)

    async def total_users(self):
        return await self.users.count_documents({})

    async def all_users(self):
        return self.users.find({})

    async def del_user(self, uid):
        await self.users.delete_one({"id": uid})

    async def ban_user(self, uid, reason="No reason"):
        await self.set_user(uid, ban=True, reason=reason)

    async def unban_user(self, uid):
        await self.set_user(uid, ban=False, reason="")

    async def banned(self):
        u = [x["id"] async for x in self.users.find({"ban": True})]
        c = [x["id"] async for x in self.chats.find({"disabled": True})]
        return u, c

    # ---------- chats ----------
    async def add_chat(self, cid, title):
        if not await self.chats.find_one({"id": cid}):
            await self.chats.insert_one({"id": cid, "title": title, "disabled": False, "reason": ""})
            return True
        return False

    async def set_chat(self, cid, **kw):
        await self.chats.update_one({"id": cid}, {"$set": kw})

    async def get_chat(self, cid):
        return await self.chats.find_one({"id": cid})

    async def total_chats(self):
        return await self.chats.count_documents({})

    async def all_chats(self):
        return self.chats.find({})

    async def del_chat(self, cid):
        await self.chats.delete_one({"id": cid})

    # ---------- bot settings (admin commands se badalti hain) ----------
    async def get_settings(self):
        return await self.settings.find_one({"_id": "bot"}) or {}

    async def set_setting(self, key, value):
        await self.settings.update_one({"_id": "bot"}, {"$set": {key: value}}, upsert=True)

    # ---------- premium ----------
    async def is_premium(self, uid):
        p = await self.premium.find_one({"id": uid})
        return bool(p and p.get("expiry_time") and p["expiry_time"] > now())

    async def get_premium(self, uid):
        return await self.premium.find_one({"id": uid})

    async def add_premium(self, uid, seconds):
        p = await self.get_premium(uid)
        base = p["expiry_time"] if p and p.get("expiry_time") and p["expiry_time"] > now() else now()
        exp = base + dt.timedelta(seconds=seconds)
        await self.premium.update_one({"id": uid}, {"$set": {"expiry_time": exp, "notified": False}}, upsert=True)
        return exp

    async def remove_premium(self, uid):
        await self.premium.delete_one({"id": uid})

    async def expired(self):
        return [x async for x in self.premium.find({"expiry_time": {"$lt": now()}})]

    async def all_premium(self):
        return [x async for x in self.premium.find({"expiry_time": {"$gt": now()}})]

    # ---------- redeem codes ----------
    async def add_code(self, code, duration):
        await self.codes.insert_one({"_id": code, "duration": duration})

    async def use_code(self, code):
        return await self.codes.find_one_and_delete({"_id": code})

    # ---------- contents ----------
    async def add_content(self, key, title, msg_id):
        await self.contents.update_one(
            {"_id": key},
            {"$set": {"title": title}, "$push": {"items": msg_id}, "$setOnInsert": {"added": now()}},
            upsert=True,
        )
        await self.demand.update_one({"_id": key}, {"$set": {"has_content": True}})

    async def get_content(self, key):
        return await self.contents.find_one({"_id": key})

    async def del_content(self, key):
        r = await self.contents.delete_one({"_id": key})
        await self.demand.update_one({"_id": key}, {"$set": {"has_content": False}})
        return r.deleted_count

    async def has_content(self, keys):
        return {x["_id"] async for x in self.contents.find({"_id": {"$in": keys}}, {"_id": 1})}

    async def list_contents(self, n=30, prefix=None):
        q = {"_id": {"$regex": f"^{prefix}"}} if prefix else {}
        return [x async for x in self.contents.find(q).sort("added", -1).limit(n)]

    async def total_contents(self):
        return await self.contents.count_documents({})

    # ---------- demand / trending ----------
    async def bump_demand(self, key, title, has):
        await self.demand.update_one(
            {"_id": key}, {"$inc": {"count": 1}, "$set": {"title": title, "has_content": has}}, upsert=True
        )

    async def top_demand(self, missing_only=False, n=20):
        q = {"has_content": False} if missing_only else {}
        return [x async for x in self.demand.find(q).sort("count", -1).limit(n)]

    async def bump_search(self, q):
        await self.searches.update_one({"_id": q}, {"$inc": {"count": 1}}, upsert=True)

    async def top_searches(self, n=15):
        return [x async for x in self.searches.find({}).sort("count", -1).limit(n)]

    # ---------- verify ----------
    async def new_token(self, uid, token):
        await self.tokens.insert_one({"uid": uid, "token": token, "used": False, "t": now()})

    async def get_token(self, uid, token):
        return await self.tokens.find_one({"uid": uid, "token": token})

    async def use_token(self, uid, token):
        await self.tokens.update_one({"uid": uid, "token": token}, {"$set": {"used": True}})

    # ---------- join requests (fsub) ----------
    async def add_join_req(self, uid, cid):
        await self.joinreq.update_one({"uid": uid}, {"$addToSet": {"ch": cid}}, upsert=True)

    async def has_joined(self, uid, cid):
        d = await self.joinreq.find_one({"uid": uid})
        return bool(d and cid in d.get("ch", []))

    async def clear_join_req(self):
        await self.joinreq.drop()

    # ---------- per-group settings ----------
    async def get_group_settings(self, gid):
        c = await self.chats.find_one({"id": gid})
        return (c or {}).get("settings", {})

    async def set_group_setting(self, gid, key, value):
        await self.chats.update_one({"id": gid}, {"$set": {f"settings.{key}": value}}, upsert=True)

    async def reset_group_settings(self, gid=None):
        q = {"id": gid} if gid else {"settings": {"$exists": True}}
        r = await self.chats.update_many(q, {"$unset": {"settings": ""}})
        return r.modified_count

    # ---------- group connections (PM se manage) ----------
    async def connect_group(self, gid, uid):
        await self.conns.update_one({"user_id": uid}, {"$addToSet": {"groups": gid}}, upsert=True)

    async def disconnect_group(self, gid, uid):
        await self.conns.update_one({"user_id": uid}, {"$pull": {"groups": gid}})
        u = await self.get_user(uid)
        if u.get("active_grp") == gid:
            await self.set_user(uid, active_grp=None)

    async def connected(self, uid):
        d = await self.conns.find_one({"user_id": uid})
        return (d or {}).get("groups", [])

    # ---------- referral ----------
    async def refer_points(self, uid):
        d = await self.refer.find_one({"user_id": uid})
        return (d or {}).get("points", 0)

    async def set_refer_points(self, uid, pts):
        await self.refer.update_one({"user_id": uid}, {"$set": {"points": pts}}, upsert=True)

    async def already_referred(self, uid):
        return bool(await self.referred.find_one({"user_id": uid}))

    async def mark_referred(self, uid):
        await self.referred.update_one({"user_id": uid}, {"$set": {"user_id": uid}}, upsert=True)

    # ---------- movie update dedupe ----------
    async def add_update_name(self, key):
        if await self.updates.find_one({"_id": key}):
            return False
        await self.updates.insert_one({"_id": key})
        return True

    async def clear_update_names(self):
        await self.updates.delete_many({})

    async def db_size(self):
        s = await self.db.command("dbstats")
        return s.get("dataSize", 0)


db = DB()
