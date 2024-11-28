# import mysql.connector
#
#
# class MySQLDatabase:
#
#     def __init__(self, host, user, password, database):
#         self.conn = mysql.connector.connect(
#             host=host, user=user, password=password, database=database
#         )
#         self.cursor = self.conn.cursor()
#
#     def fetch_closest_question(self, query: str):
#         sql_query = "SELECT question, answer FROM faq"
#         self.cursor.execute(sql_query)
#         rows = self.cursor.fetchall()
#
#         # Perform basic similarity matching (or replace with advanced NLP if needed)
#         best_match = None
#         highest_similarity = 0
#
#         for question, answer in rows:
#             similarity = len(set(query.lower().split()) & set(question.lower().split()))
#             if similarity > highest_similarity:
#                 best_match = (question, answer)
#                 highest_similarity = similarity
#
#         return best_match if best_match else ("No match found", "I'm sorry, I don't have an answer for that.")
#
#     def close(self):
#         self.cursor.close()
#         self.conn.close()