import pywhatkit
import pyautogui
massage = '''
    Name: عبدالرحمن خالد سعد الدين
    ID: 220769
    Course: Comp 304 Compiler Design - Spring
    Score after adding extra bonus
    (midterm,lab,oral,total): 12/15, 15/37, 5/8, 32/60.
    This is a fully automated message.
    Good luck ^_^
    '''
pywhatkit.sendwhatmsg_instantly("+201120844781", massage,tab_close=True, close_time=1)

pyautogui.press("enter")

# pywhatkit.sendwhatmsg_to_group_instantly("BtqjmnnrQHO5rabWZ8Uq8u", "testing same thing",tab_close=True)
# pyautogui.press("enter")