import sys

class cli:
    def user_menu(self, question, list):
        response = ''
        if question:
            print(question)
        for v in list:
            print(v + "\n")
        
        response = sys.stdin

        return response

    def user_question(self, question):
        print(question)
        response = sys.stdin
        return response
    
    