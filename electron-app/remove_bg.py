import sys
from PIL import Image

def process_image(input_path, output_path):
    try:
        img = Image.open(input_path).convert("RGBA")
        datas = img.getdata()

        newData = []
        for item in datas:
            # Check for the light green/yellowish background
            # The background in the image is approx rgb(215, 235, 180) to rgb(230, 250, 200)
            if item[0] > 180 and item[1] > 200 and item[2] > 150 and item[0] < 240 and item[1] < 255 and item[2] < 220:
                newData.append((255, 255, 255, 0)) # transparent
            # Also remove some of the door gray (rgb 160-190)
            elif item[0] > 150 and item[1] > 150 and item[2] > 120 and item[0] < 190 and item[1] < 190 and item[2] < 170 and abs(item[0]-item[1]) < 30:
                newData.append((255, 255, 255, 0))
            else:
                newData.append(item)

        img.putdata(newData)
        
        # We can also just crop it to a circle which guarantees a perfect look
        # Let's do a circular crop mask
        width, height = img.size
        mask = Image.new('L', (width, height), 0)
        from PIL import ImageDraw
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, width, height), fill=255)
        
        result = Image.new('RGBA', (width, height))
        result.paste(img, (0, 0), mask=mask)

        result.save(output_path, "PNG")
        print("Success")
    except Exception as e:
        print("Error:", e)

process_image('/Users/ostap/.gemini/antigravity/brain/225d5339-b7b3-4e43-aa5c-1555ba8c42a9/media__1778697516338.jpg', '/Users/ostap/pc-controller/electron-app/src/renderer/assets/fluttershy.png')
