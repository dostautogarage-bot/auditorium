import os, glob

for filepath in glob.glob('booking/templates/booking/*.html') + ['booking/views.py']:
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Do safe replaces
    content = content.replace('Grand Auditorium', 'ABC Auditorium')
    content = content.replace('>Auditorium<', '>ABC Auditorium<')
    content = content.replace('— Auditorium', '— ABC Auditorium')
    content = content.replace('- Auditorium', '- ABC Auditorium')
    content = content.replace('Auditorium Portal', 'ABC Auditorium Portal')
    content = content.replace('auditorium portal', 'ABC Auditorium portal')
    content = content.replace('Auditorium Schedule', 'ABC Auditorium Schedule')
    content = content.replace('"Auditorium Booking System"', '"ABC Auditorium Booking System"')
    content = content.replace('"Auditorium"', '"ABC Auditorium"')
    content = content.replace("'Auditorium'", "'ABC Auditorium'")
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
print('Done!')
