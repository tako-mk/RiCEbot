import json

tracks = []

with open("track.txt", "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            aliases_part, name, image = line.split(":", 2)  # ここで2つだけ分割
            aliases = aliases_part.split(",")
            tracks.append({
                "aliases": aliases,
                "name": name,
                "image": image
            })
        except Exception as e:
            print("エラー行:", line)

with open("track.json", "w", encoding="utf-8") as f:
    json.dump(tracks, f, ensure_ascii=False, indent=2)

print("全コースを track.json に書き出しました。")
