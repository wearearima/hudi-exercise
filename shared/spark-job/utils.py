import re
from datetime import datetime


class Utils:

    @staticmethod
    def get_title(content):
        content = content.strip()
        title = ''
        try:
            if(content != ''):
                arr = content.split("\n", 2)
                title = arr[1]
        except:
            title = ''
        return title

    @staticmethod
    def get_content(content):
        content = content.strip()
        actual_content = ''
        try:
            if(content != ''):
                arr = content.split("\n", 2)
                actual_content = arr[2]
        except:
            actual_content = ''
        return actual_content

    @staticmethod
    def get_date_timestamp(content):
        content = content.strip()
        content = content[:150]
        date = ''
        # Checking for format like 12 August 1993
        list1 = re.findall(r"[\d]{1,2} [ADFJMNOS]\w* [\d]{4}", content)
        # Checking for format like August 12, 1993
        list2 = re.findall(r"[ADFJMNOS]\w* [\d]{1,2}[,] [\d]{4}", content)
        try:
            if(len(list1) > 0):
                date = datetime.strptime(
                    str(list1[0]), "%d %B %Y").strftime("%m/%d/%Y")
            elif(len(list2) > 0):
                date = datetime.strptime(
                    str(list2[0]), "%B %d, %Y").strftime("%m/%d/%Y")
            else:
                date = ''
        except:
            date = ''
        return date

    @staticmethod
    def check_if_person(date):
        if(date != ''):
            return True
        return False
