from PIL import Image
import hero
frames = hero.hero_frames(); ranges = hero.frame_ranges()
picks = [("down","idle",0),("down","idle",1),("down","move",0),("down","attack",0),("down","attack",1),("down","hurt",0),("down","death",2),("side","idle",0),("side","attack",1),("up","idle",0)]
sheet = Image.new("RGBA",(len(picks)*48,56),(28,32,42,255))
for i,(f,s,idx) in enumerate(picks):
    start,count = ranges[f"{f}:{s}"]
    sheet.alpha_composite(frames[start+idx],(i*48,0))
sheet = sheet.resize((sheet.width*8, sheet.height*8), Image.NEAREST)
sheet.save("closeup2.png")
print("ok")
