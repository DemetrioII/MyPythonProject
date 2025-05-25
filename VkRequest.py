from functions import *
import json
import httpx
import asyncio
from fastapi import FastAPI, HTTPException

VK_SERVICE_KEY = "fea2d7a3fea2d7a3fea2d7a30efd8e133dffea2fea2d7a39947b135431f0ea0ac217ce9"
VK_API_VERSION = "5.199"

app = FastAPI()

@app.get("/full-profile", tags=["Агрегированный профиль"])
async def get_full_profile(link: str):
    user_id = int(await parse(link))
    url = "https://api.vk.com/method/"
    token = VK_SERVICE_KEY
    version = "5.199"
    async with httpx.AsyncClient() as client:
        try:
            base_info = client.get(f"{url}users.get", params={
                "access_token": token,
                "user_ids": user_id,
                "v": version,
                "fields": "bdate, sex, city, relation, last_seen"
            })

            groups = client.get(f"{url}groups.get", params={
                "access_token": token,
                "user_id": user_id,
                "v": version,
                "extended": 1,
                "fields": "activity, age_limits"
            })

            wall = client.get(f"{url}wall.get", params={
                "access_token": token,
                "domain": user_id,
                "v": version
            })

            friends = client.get(f"{url}friends.get", params={
                "access_token": token,
                "user_id": user_id,
                "v": version,
                "fields": "sex,city"
            })

            followers = client.get(f"{url}users.getFollowers", params={
                "access_token": token,
                "user_id": user_id,
                "v": version,
                "fields": "sex,city"
            })
        except httpx.RequestError as e:
            raise HTTPException(status_code=503, detail=f"VK API request failed: {str(e)}")

        try:
            responses = await asyncio.gather(base_info, groups, wall, friends, followers)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error processing VK responses: {str(e)}")
        try:
            data = {
                "base_info": responses[0].json().get("response", {}),
                "groups": responses[1].json().get("response", {}),
                "wall": responses[2].json().get("response", {}),
                "friends": responses[3].json().get("response", {}),
                "followers": responses[4].json().get("response", {})
            }

            for info, answer in data.items():
                if not answer:
                    continue
                if info == "base_info":
                    data[info] = answer[0]
                if info == "groups":
                    fields_to_keep = {'is_closed', 'deactivated', 'activity', 'age_limits', 'ban_info', 'is_favorite'}
                    value_to_age = {1: 0, 2: 16, 3: 18}
                    for item in data[info]['items']:
                        keys = list(item.keys())
                        for key in keys:
                            if key not in fields_to_keep:
                                del item[key]
                            if key == "age_limits":
                                item[key] = value_to_age.get(item[key], item[key])
                if info == "wall":
                    if "reaction_sets" in answer:
                        del data[info]["reaction_sets"]

                    fields_to_keep = {'marked_as_ads', 'date', 'from_id', 'id', 'reactions', 'owner_id', 'views'}
                    for item in data[info]['items']:
                        keys = list(item.keys())
                        for key in keys:
                            if key not in fields_to_keep:
                                del item[key]
                            if key == "views":
                                item[key] = item["views"].get("count")
                            if key == "reactions":
                                item[key] = item["reactions"].get("count")

                if info == "friends":
                    fields_to_keep = {'id', 'deactivated', 'sex', 'first_name', 'last_name', 'can_access_closed',
                                      'is_closed', 'city'}
                    for item in data[info]['items']:
                        keys = list(item.keys())
                        for key in keys:
                            if key not in fields_to_keep:
                                del item[key]
                if info == "followers":
                    fields_to_keep = {'id', 'deactivated', 'sex', 'first_name', 'last_name', 'can_access_closed',
                                      'is_closed', 'city'}
                    for item in data[info]['items']:
                        keys = list(item.keys())
                        for key in keys:
                            if key not in fields_to_keep:
                                del item[key]
            return json.dumps(data)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error processing profile data: {str(e)}")


@app.get("/metrics", tags=["Расчет метрик"])
async def get_metrics():
    metrics = dict()
    # Тут должно быть подключение к базе данных
    with open("data.json", "r", encoding="UTF-8") as f:
        raw_data = json.load(f)
    data = json.loads(raw_data)
    for key, info in data.items():
        if key == "base_info":
            relationship_status = {
                0: "не указано",
                1: "не женат/не замужем",
                2: "есть друг/есть подруга",
                3: "помолвлен/помолвлена",
                4: "женат/замужем",
                5: "всё сложно",
                6: "в активном поиске",
                7: "влюблён/влюблена",
                8: "в гражданском браке"
            }
            sex_status = {
                1: "Ж",
                2: "М"
            }
            metrics[key] = info.copy()
            try:
                metrics[key]["relation"] = relationship_status[metrics[key]["relation"]]
            except KeyError:
                pass
            try:
                metrics[key]["sex"] = sex_status[metrics[key]["sex"]]
            except KeyError:
                pass

        elif key == "groups":
            metrics[key] = dict()
            metrics[key]["count"] = info.get("count", 0)
            items = info.get("items", [])
            for item in items:
                for tag, value in item.items():
                    if tag not in metrics[key].keys():
                        metrics[key][tag] = dict()
                    metrics[key][tag][value] = metrics[key][tag].get(value, 0) + 1

        elif key == "wall":
            metrics[key] = dict()
            items = info.get("items", [])

            metrics[key]["last_post"] = items[0].get("date", 0) if items else 0
            total_reactions = sum(item.get('reactions', 0) for item in items)
            total_views = sum(item.get('views', 0) for item in items)
            metrics[key]["social_activity"] = (total_reactions / total_views) * 100 if total_views else 0
            marked_ads = sum(item.get('marked_as_ads', 0) for item in items)
            post_count = info.get("count", 0)
            metrics[key]["post_count"] = post_count
            metrics[key]["ads_to_posts"] = marked_ads / post_count if post_count else 0

        elif key == "friends":
            metrics[key] = dict()
            items = info.get("items", [])
            allow_tags = {"city", "sex"}
            for item in items:
                for tag, value in item.items():
                    if tag in allow_tags:
                        if tag not in metrics[key].keys():
                            metrics[key][tag] = dict()
                        if tag == "city":
                            metrics[key][tag][value.get("title", "Unknown")] = metrics[key][tag].get(
                                value.get("title", "Unknown"), 0) + 1
                        elif tag == "sex":
                            metrics[key][tag][value] = metrics[key][tag].get(value, 0) + 1
        elif key == "followers":
            metrics[key] = dict()
            items = info.get("items", [])
            allow_tags = {"city", "sex"}
            for item in items:
                for tag, value in item.items():
                    if tag in allow_tags:
                        if tag not in metrics[key].keys():
                            metrics[key][tag] = dict()
                        if tag == "city":
                            metrics[key][tag][value.get("title", "Unknown")] = metrics[key][tag].get(
                                value.get("title", "Unknown"), 0) + 1
                        elif tag == "sex":
                            metrics[key][tag][value] = metrics[key][tag].get(value, 0) + 1
        else:
            metrics[key] = dict()
        print(key, info)

    return metrics
