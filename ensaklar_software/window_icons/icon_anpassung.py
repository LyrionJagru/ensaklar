# -*- coding: utf-8 -*-
"""
Created on Tue Apr 14 11:31:23 2026

@author: jbgru
"""

from PIL import Image

img = Image.open("window_icons/app_icon.ico")
print(img.mode)

#%%

from PIL import Image

img = Image.open("Window_icons/app_icon.png").convert("RGBA")
data = img.getdata()

new_data = []
for item in data:
    r, g, b, a = item
    if r > 245 and g > 245 and b > 245:
        new_data.append((255, 255, 255, 0))
    else:
        new_data.append((r, g, b, a))

img.putdata(new_data)

img.save(
    "Window_icons/app_icon_v1.ico",
    format="ICO",
    sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
)

#%%
from PIL import Image

img = Image.open("window_icons/app_icon.png").convert("RGBA")
alpha = img.getchannel("A")
min_alpha, max_alpha = alpha.getextrema()

print("Min Alpha:", min_alpha)
print("Max Alpha:", max_alpha)

#%%
from PIL import Image

img = Image.open("window_icons/app_icon.png").convert("RGBA")

# Schwellenwert für grau/weiß Hintergrund
threshold = 200  # Anpassen, falls nötig (je nach Grauton)

data = img.getdata()
new_data = []
for r, g, b, a in data:
    # Alle Kanäle hell genug → transparent machen
    if r > threshold and g > threshold and b > threshold:
        new_data.append((255, 255, 255, 0))  # Transparent
    else:
        new_data.append((r, g, b, a))

img.putdata(new_data)

# Als PNG speichern (zur Kontrolle)
img.save("window_icons/app_icon_transparent.png", "PNG")

# Als ICO speichern
img.save(
    "Window_icons/app_icon.ico",
    format="ICO",
    sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
)