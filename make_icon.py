"""Creates detent.ico for the exe/installer."""
from app import make_icon
make_icon(True).resize((256, 256)).save("detent.ico", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
print("detent.ico written")
