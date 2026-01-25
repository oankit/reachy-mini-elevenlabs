"""Create a simple icon for the ElevenLabs app."""
from PIL import Image, ImageDraw

# Create a 200x200 image with light gray background
img = Image.new('RGB', (200, 200), color='#f0f0f0')
draw = ImageDraw.Draw(img)

# Draw two vertical bars (left half blocks)
# Left bar - purple
draw.rectangle([50, 40, 85, 160], fill='#7c3aed')
# Right bar - lighter purple  
draw.rectangle([115, 40, 150, 160], fill='#a78bfa')

# Save as PNG
img.save('reachy_mini_elevenlabs/images/icon.png')
print("Icon created successfully!")
