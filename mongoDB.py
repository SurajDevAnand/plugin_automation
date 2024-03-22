#!/usr/bin/bash
import os
import subprocess
import json
import warnings
import urllib.parse
import urllib.request


warnings.filterwarnings("ignore")

def move_folder(source, destination):
    try:
        os.rename(source, destination)
    except Exception as e:
        print(str(e))
        return False
    return True


def move_plugin(plugin_name, plugins_temp_path, agent_plugin_path):
    try:
        if not check_directory(agent_plugin_path):
            print(f"    {agent_plugin_path} Agent Plugins Directory not Present")
            return False
        if not move_folder(plugins_temp_path+plugin_name, agent_plugin_path+plugin_name): 
            return False

    except Exception as e:
        print(str(e))
        return False
    return True


def plugin_config_setter(plugin_name, plugins_temp_path, arguments):
    try:
        full_path=plugins_temp_path+plugin_name+"/"
        config_file_path=full_path+plugin_name+".cfg"

        arguments='\n'.join(arguments.replace("--","").split())
        with open(config_file_path, "w") as f:
            f.write(f"[mongoDB]\n"+arguments)


    except Exception as e:
        print(str(e))
        return False
    return True


def plugin_validator(output):
    try:
        result=json.loads(output.decode())
        if "status" in result:
            if result['status']==0:
                print("Plugin execution encountered a error")
                if "msg" in result:
                    print(result['msg'])
            return False

    except Exception as e:
        print(str(e))
        return False
    
    return True



def download_file(url, path):
    filename=url.split("/")[-1]
    full_path=path+filename
    urllib.request.urlretrieve(url, full_path)
    response=urllib.request.urlopen(url)
    if response.getcode() == 200 :
        print(f"      {filename} Downloaded")
    else:
        print(f"      {filename} Download Failed with response code {str(response.status_code)}")
        return False
    return True


def down_move(plugin_name, plugin_url, plugins_temp_path):
    temp_plugin_path=os.path.join(plugins_temp_path,plugin_name+"/")
    if not check_directory(temp_plugin_path):
        if not make_directory(temp_plugin_path):return False

    py_file_url=plugin_url+plugin_name+"/"+plugin_name+".py"
    cfg_file_url=plugin_url+plugin_name+"/"+plugin_name+".cfg"
    if not download_file(py_file_url, temp_plugin_path):return False
    if not download_file(cfg_file_url, temp_plugin_path):return False
    return True


def execute_command(cmd, need_out=False):
    try:
        cmd=cmd.split()
        result=subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode != 0:
            print(f"    {cmd} execution failed with return code {result.returncode}")
            print(f"    {str(result.stderr)}")
            return False
        if need_out:
            return result.stdout
        return True
    except Exception as e:
        print(    str(e))
        return False

def make_directory(path):

    if not check_directory(path):
        try:
            os.mkdir(path)
            print(f"    {path} directory created.")
        
        except Exception as e:
             return False
    return True


def check_directory(path):
    return os.path.isdir(path)


def mongod_server(args):
        
        try:
            if(args.admin_username!="None" and args.admin_password!="None" and args.authdb!="None"):
                mongod_server = "{0}:{1}@{2}:{3}/{4}".format(args.admin_username,urllib.parse.quote(args.admin_password), args.host, args.port, args.authdb)
            elif(args.admin_username!="None" and args.admin_password!="None"):
                mongod_server = "{0}:{1}@{2}:{3}".format(args.admin_username, args.admin_password, args.host, args.port)
            elif(args.authdb!="None"):
                mongod_server = "{0}:{1}/{2}".format(args.host, args.port, args.authdb)
            else:
                mongod_server = "{0}:{1}".format(args.host, args.port)
            return mongod_server
        
        except Exception as e:
            print( str(e))
            return False

def mongo_connect(args):
    try:
        
        import pymongo
        from pymongo import MongoClient
        mongod_server_string=mongod_server(args)
        mongo_uri = 'mongodb://' + mongod_server_string
        if args.tls:
            connection = MongoClient(mongo_uri, serverSelectionTimeoutMS=10000,tls=args.tls,tlscertificatekeyfile=args.tlscertificatekeyfile,tlscertificatekeyfilepassword=args.tlscertificatekeyfilepassword,tlsallowinvalidcertificates=args.tlsallowinvalidcertificates)
        else:
            connection = MongoClient(mongo_uri, serverSelectionTimeoutMS=10000)

        return connection

    except Exception as e:
        print( str(e))
        return False

def check_user(db, args):     

    mongo_users = db.system.users.find()

    for mongo_user in mongo_users:
        if mongo_user['user']==args.site24x7_user:
            for role in mongo_user['roles']:
                if role['role'] == "clusterMonitor":
                    return True
                else:
                    print("User does not have clusterMonitor role")
                    return False
    return False

def create_user(args):
    try:
        connection=mongo_connect(args)
        if not connection:
            return False
        db=connection[args.dbname]
        if check_user(db, args):
            return True
        roles = [
            {
                "role": "clusterMonitor",
                "db": "admin" 
            }
        ]
        db.command("createUser", args.site24x7_user, pwd=args.site24x7_pass, roles=roles)
        connection.close()
        return True

    except Exception as e:
        connection.close()
        print(  str(e))
        return False

def initiate(plugin_name, plugin_url, args=None):

    print("------------------------------ Starting Plugin Automation ------------------------------")
    print()
    
    #Installing python module dependencies
    cmd="""pip3 install pymongo"""
    print("    Installing pymongo python module")
    if not execute_command(cmd):
        print("")
        print("------------------------------ Plugin Automation Failed ------------------------------")
        return 
    print("    Installed pymongo python module")
    print()
    
    print(f"    Creating Site24x7 Plugin User \"{site24x7_user}\"")
    if not create_user(args):
        print("")
        print("------------------------------ Plugin Automation Failed ------------------------------")
        return 
    print(f"    Site24x7 Plugin User \"{site24x7_user}\" created / Exist")
    print()  

    agent_path="/opt/site24x7/monagent/" 
    agent_temp_path=agent_path+"temp/"
    agent_plugin_path=agent_path+"plugins/"

    # checking the existance of Agent Temporary Directory
    if not check_directory(agent_temp_path):
        print("    Agent Directory does not Exist")
        print("------------------------------ Plugin Automation Failed ------------------------------")
        return
    
    # Creating the Agent Plugin Temporary Directory
    print("    Creating Temporary Plugins Directory")
    plugins_temp_path=os.path.join(agent_temp_path,"plugins/")
    if not check_directory(plugins_temp_path):
        if not make_directory(plugins_temp_path):
            print("")
            print("------------------------------ Plugin Automation Failed ------------------------------")
            return 
    print("    Created Temporary Plugins Directory")
    print()

    print("    Creating Temporary Plugins Modules Directory")
    modules_temp_path=os.path.join(plugins_temp_path,"modules/")
    if not check_directory(modules_temp_path):
        if not make_directory(modules_temp_path):
            print("")
            print("------------------------------ Plugin Automation Failed ------------------------------")
            return 
    print("    Created Temporary Plugins Modules Directory")
    print()


    # Downloading the files from GitHub
    print("    Downloading Plugin Files")
    if not down_move(plugin_name, plugin_url, plugins_temp_path):
       print("")
       print("------------------------------ Plugin Automation Failed ------------------------------")
       return 
    print("    Downloaded Plugin Files")
    print()

    # Setting Executable Permissions for the Plugin
    print("    Creating executable plugin file")
    cmd=f"chmod 744 {plugins_temp_path}/{plugin_name}/{plugin_name}.py"
    if not execute_command(cmd):
        print("")
        print("------------------------------ Plugin Automation Failed ------------------------------")
        return 
    print("    Created executable plugin file")
    print("")

    # Validating the plugin output
    print("    Validating the python plugin output")
    if not args:
        cmd=f"{plugins_temp_path}/{plugin_name}/{plugin_name}.py"
    else:
        arguments=f"--username={args.site24x7_user} --password={args.site24x7_pass} --host={args.host} --port={args.port} --dbname={args.dbname} --authdb={args.authdb} --tls={args.tls} --tlscertificatekeyfile={args.tlscertificatekeyfile} --tlscertificatekeyfilepassword={args.tlscertificatekeyfilepassword} --tlsallowinvalidcertificates={args.tlsallowinvalidcertificates} "
        cmd=f"{plugins_temp_path}/{plugin_name}/{plugin_name}.py" + " "+arguments

    result=execute_command(cmd, need_out=True)
    if not plugin_validator(result):
        print("")
        print("------------------------------ Plugin Automation Failed ------------------------------")
        return
    print("    Plugin output validated sucessfully")
    print("")

    if args:
        # Setting the plugin config file
        print("    Setting plugin configuration")
        if not plugin_config_setter(plugin_name, plugins_temp_path, arguments):
            print("")
            print("------------------------------ Plugin Automation Failed ------------------------------")
            return 
        print("    Plugin configuration set sucessfully")
        print()
    
    # Moving the plugin files into the Agent Directory
    print("    Moving the plugin into the Site24x7 Agent directory")
    if not move_plugin(plugin_name, plugins_temp_path, agent_plugin_path):
        print("")
        print("------------------------------ Plugin Automation Failed ------------------------------")
        return 
    print("    Moved the plugin into the Site24x7 Agent directory")
    print()


    print("------------------------------ Sucessfully Completed Plugin Automation ------------------------------")


if __name__ == "__main__":
    plugin_name="mongoDB"
    plugin_url="https://raw.githubusercontent.com/site24x7/plugins/master/"

    #user configs
    host = "localhost"
    port = 27017
    admin_username = "myUserAdmin"
    admin_password = "abc123"
    site24x7_user="plugin_user"
    site24x7_pass='plugin@123'
    dbname = "admin"
    authdb = "admin"

    # TLS/SSL Details
    tls=False
    tlscertificatekeyfile=None
    tlscertificatekeyfilepassword=None
    tlsallowinvalidcertificates="True"


    admin_username=input("\n Enter the Admin User of the MongoDB Instance : ")
    if not admin_username: print("No Admin User Entered");exit()

    admin_password=input("\n Enter the Password of the MongoDB Instance : ")
    if not admin_password: print("No Admin User Password Entered");exit()

    site24x7_user=input("\n Enter the Username to be created in the MongoDB Instance : ") or "site24x7_plugin"
    if not site24x7_user: print("No Username Entered, using default user \"site24x7_plugin\"")

    site24x7_pass=input(f"\n Enter the password for the user \'{site24x7_user}\' to be created in the MongoDB Instance : ")
    if not site24x7_pass: print("No password Entered");exit()

    host=input("\n Enter the hostname where the MongoDB Instance is running (default option: \"localhost\") : ") or "localhost"

    port=input("\n Enter the port where the MongoDB Instance is running (dafault option: \"27017\"): ") or "27017"

    dbname=input("\n Enter the MongoDB DB name to connect (default option: \"admin\") : ") or "admin"
    authdb=input("\n Enter the MongoDB Auth DB name to connect (default option: \"admin\") : ") or "admin"





    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--host', help='hostname for mongoDB',default=host)
    parser.add_argument('--port', help='port number for mongoDB',default=port)
    parser.add_argument('--admin_username', help='username for mongoDB',default=admin_username)
    parser.add_argument('--admin_password', help='password for mongoDB',default=admin_password)
    parser.add_argument('--site24x7_user', help='site24x7_username for mongoDB',default=site24x7_user)
    parser.add_argument('--site24x7_pass', help='site2=4x7_password for mongoDB',default=site24x7_pass)
    parser.add_argument('--dbname', help='hostname for mongoDB',default=dbname)
    parser.add_argument('--authdb', help='port number for mongoDB',default=authdb)
    parser.add_argument('--tls' ,help="tls setup (True or False)",nargs='?',default= tls)
    parser.add_argument('--tlscertificatekeyfile' ,help="tlscertificatekeyfile file path",default= tlscertificatekeyfile)
    parser.add_argument('--tlscertificatekeyfilepassword' ,help="tlscertificatekeyfilepassword",default= tlscertificatekeyfilepassword)
    parser.add_argument('--tlsallowinvalidcertificates' ,help="tlsallowinvalidcertificates",default= tlsallowinvalidcertificates)

    args=parser.parse_args()

    initiate(plugin_name, plugin_url, args)