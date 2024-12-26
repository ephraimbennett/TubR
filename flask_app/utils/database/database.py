import mysql.connector
import glob
import json
import csv
from io import StringIO
import itertools
import hashlib
import os
import cryptography
from cryptography.fernet import Fernet
from math import pow

class database:

    def __init__(self, purge = False):

        # Grab information from the configuration file
        self.database       = 'db'
        self.host           = '127.0.0.1'
        self.user           = 'master'
        self.port           = 3306
        self.password       = 'master'
        self.tables         = ['users', 'users', 'boards', 'board_members', 'lists', 'cards']
        
        # NEW IN HW 3-----------------------------------------------------------------
        self.encryption     =  {   'oneway': {'salt' : b'averysaltysailortookalongwalkoffashortbridge',
                                                 'n' : int(pow(2,5)),
                                                 'r' : 9,
                                                 'p' : 1
                                             },
                                'reversible': { 'key' : '7pK_fnSKIjZKuv_Gwc--sZEMKn2zc8VvD6zS96XcNHE='}
                                }
        #-----------------------------------------------------------------------------

    def query(self, query = "SELECT * FROM users", parameters = None):

        cnx = mysql.connector.connect(host     = self.host,
                                      user     = self.user,
                                      password = self.password,
                                      port     = self.port,
                                      database = self.database,
                                      charset  = 'latin1'
                                     )


        if parameters is not None:
            cur = cnx.cursor(dictionary=True)
            cur.execute(query, parameters)
        else:
            cur = cnx.cursor(dictionary=True)
            cur.execute(query)

        # Fetch one result
        row = cur.fetchall()
        cnx.commit()

        if "INSERT" in query:
            cur.execute("SELECT LAST_INSERT_ID()")
            row = cur.fetchall()
            cnx.commit()
        cur.close()
        cnx.close()
        return row

    def createTables(self, purge=False, data_path = 'flask_app/database/'):
        ''' FILL ME IN WITH CODE THAT CREATES YOUR DATABASE TABLES.'''

        #should be in order or creation - this matters if you are using forign keys.
         
        if purge:
            for table in self.tables[::-1]:
                self.query(f"""DROP TABLE IF EXISTS {table}""")
            
        # Execute all SQL queries in the /database/create_tables directory.
        for table in self.tables:
            
            #Create each table using the .sql file in /database/create_tables directory.
            with open(data_path + f"create_tables/{table}.sql") as read_file:
                create_statement = read_file.read()
            self.query(create_statement)

            # Import the initial data
            try:
                params = []
                with open(data_path + f"initial_data/{table}.csv") as read_file:
                    scsv = read_file.read()            
                for row in csv.reader(StringIO(scsv), delimiter=','):
                    params.append(row)
            
                # Insert the data
                cols = params[0]; params = params[1:] 
                self.insertRows(table = table,  columns = cols, parameters = params)
            except:
                print('no initial data')

    def insertRows(self, table='table', columns=['x','y'], parameters=[['v11','v12'],['v21','v22']]):
        
        # Check if there are multiple rows present in the parameters
        has_multiple_rows = any(isinstance(el, list) for el in parameters)
        keys, values      = ','.join(columns), ','.join(['%s' for x in columns])
        
        # Construct the query we will execute to insert the row(s)
        query = f"""INSERT IGNORE INTO {table} ({keys}) VALUES """
        if has_multiple_rows:
            for p in parameters:
                query += f"""({values}),"""
            query     = query[:-1] 
            parameters = list(itertools.chain(*parameters))
        else:
            query += f"""({values}) """                      
        
        insert_id = self.query(query,parameters)[0]['LAST_INSERT_ID()']         
        return insert_id
    
    def verifyMembers(self, members):
        # get the members
        sql = "SELECT email FROM users WHERE email=%s"
        emails = None
        try:
            emails_row = self.query(sql, members)
        except Exception as e:
            print("ddd")
            print(e)
            return {'success:': 0, 'message': 'Could not find users.'}
        emails = []
        for row in emails_row:
            emails.append(row['email'])
        for member in members:
            if member not in emails:
                return {'success': 0, 'message': 'User(s) do not exist'}
        return {'success' : 1, 'message': 'Users exist.'}
        
    
    def createBoard(self, name, description, owner, users):

        # get the id of the user who is going to own the board
        owner_id = self.query("SELECT * FROM users WHERE email=%s", [owner])[0]['user_id']

        select_sql = "SELECT * FROM boards WHERE owner_id = %s"
        board_exists = self.query(select_sql, [owner])

        if len(board_exists) != 0:
            return {'success': 0, 'message': 'Board already exists.'}
        
        # make the board
        values = [name, description, owner_id]
        board_sql = "INSERT INTO boards (name, description, owner_id) VALUES (%s, %s, %s)"
        
        try:
            self.query(board_sql, values)
        except Exception as e:
            print(e)
            return {'success': 0, 'message' : 'Failed to create boards.'}
        

        # make the default lists
        # need to grab the id of the board just added
        board_id = self.query('SELECT board_id FROM boards WHERE name=%s', [name])[0]['board_id']
        list_sql = """
            INSERT INTO lists (board_id, name, position) 
            VALUES (%s, %s, %s), (%s, %s, %s), (%s, %s, %s);
            """
        list_params = [board_id, "To Do", 0, board_id, "Doing", 1, board_id, "Completed", 2]
        try:
            self.query(list_sql, list_params)
        except Exception as e:
            print(e)
            return {'success': 0, 'message': 'Failed to create default lists.'}
        
        # need to add users to the bridge table
        bridge_sql = """
            INSERT INTO board_members (board_id, user_id, role)
            VALUES (%s, %s, %s)
            """
        bridge_params = [board_id, owner_id, 'owner']
        for user in users:
            bridge_sql += ", (%s, %s, %s)"
            user_id = self.query("SELECT user_id FROM users WHERE email=%s", [user])
            if len(user_id) == 0:
                return {'success' : 0, 'message': 'Failed to add users.'}
            user_id = user_id[0]['user_id']
            bridge_params += [board_id, user_id, 'member']
        
        try:
            self.query(bridge_sql, bridge_params)
        except Exception as e:
            print(e)
            return {'success' : 0, 'message': 'Failed to add users.'}

        
        
        return {'success': 1}
    
    def getBoards(self, user):
        # get the id of the user who is going to own the board
        user_id = None
        try:
            user_id = self.query("SELECT * FROM users WHERE email=%s", [user])[0]['user_id']
            print(user_id)
        except Exception as e:
            print(e)
            return []

        select_sql = "SELECT * FROM board_members WHERE user_id = %s"
        memberships = self.query(select_sql, [user_id])
        boards = []
        for membership in memberships:
            boards.append(self.query("SELECT * FROM boards WHERE board_id=%s", [membership['board_id']])[0])
        return boards
    
    def addCard(self, list_id, title, description, position):
        sql = """INSERT INTO cards (list_id, title, description, position) VALUES (%s, %s, %s, %s);
            """
        id = None
        try:
            return self.query(sql, [list_id, title, description, position])[0]['LAST_INSERT_ID()']
            
        except Exception as e:
            print(e)
            return 0
    
    def updateCard(self, card_id, description):
        sql = """
            UPDATE cards
            SET description = %s
            WHERE card_id = %s;
            """
        try:
            return self.query(sql, [description, card_id])
        except Exception as e:
            print(e)
            return 0
    
    def deleteCard(self, card_id):
        sql = """
            DELETE FROM cards
            WHERE card_id = %s;
            """
        try:
            return self.query(sql, [card_id])
        except Exception as e:
            print(e)
            return 0
        
    def moveCard(self, card_id, new_list, new_position):
        sql = """
            UPDATE cards
            SET list_id = %s, position = %s
            WHERE card_id = %s;
            """
        try:
            return self.query(sql, [new_list, new_position, card_id])
        except Exception as e:
            print(e)
            return 0
    def addList(self, list_name, board_id, position):
        sql = """
                INSERT INTO lists (board_id, name, position) VALUES (%s, %s, %s)
                """
        try:
            return self.query(sql, [board_id, list_name, position])[0]['LAST_INSERT_ID()']
        except Exception as e:
            print(e)
            return 0
        
    def reorderList(self, new_order):
        sql = """
            UPDATE lists
            SET position=%s
            WHERE list_id=%s
            """
        i = 0
        for l in new_order:
            try:
                self.query(sql, [i, l])
                i += 1
            except Exception as e:
                print(e)
                return 0
        return 1
                
        
            
        
        

    
    
#######################################################################################
# AUTHENTICATION RELATED
#######################################################################################
    def createUser(self, email='me@email.com', password='password', role='user'):
        select_sql = "SELECT * FROM users WHERE email = %s"
        current_emails = self.query(select_sql, [email])

        if len(current_emails) != 0:
            return {'success': -1}


        values = (role, email, self.onewayEncrypt(password))
        sql = "INSERT INTO users (role, email, password) VALUES ('{}', '{}', '{}')".format(*values)

        try:
            self.query(sql)
        except Exception as e:
            return {'success': 0}

        return {'success': 1}

    def authenticate(self, email='me@email.com', password='password'):
        sql = f"SELECT * FROM users WHERE email='{email}'"
        row = self.query(sql)
        print(row)
        if len(row) == 0:
            return {'success': 0}
        if row[0]['password'] == self.onewayEncrypt(password):
            return {'success': 1}
        else:
            return {'success': 0}
    
    def isOwner(self, email='me@email.com'):
        sql = f"SELECT * FROM users WHERE email='{email}'"
        row = self.query(sql)
        if len(row) == 0:
            return False
        if row[0]['role'] == 'owner':
            return True
        return False

    def onewayEncrypt(self, string):
        encrypted_string = hashlib.scrypt(string.encode('utf-8'),
                                          salt = self.encryption['oneway']['salt'],
                                          n    = self.encryption['oneway']['n'],
                                          r    = self.encryption['oneway']['r'],
                                          p    = self.encryption['oneway']['p']
                                          ).hex()
        return encrypted_string


    def reversibleEncrypt(self, type, message):
        fernet = Fernet(self.encryption['reversible']['key'])
        
        if type == 'encrypt':
            message = fernet.encrypt(message.encode())
        elif type == 'decrypt':
            message = fernet.decrypt(message).decode()

        return message
    
    def authorizeBoard(self, user, board_id):
        user_id = self.query("SELECT user_id FROM users WHERE email=%s", [user])[0]['user_id']
        user_boards = self.query("SELECT board_id FROM board_members WHERE user_id=%s", [user_id])

        for row in user_boards:
            if row['board_id'] == board_id:
                return True
        return False


