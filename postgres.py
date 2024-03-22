#! /usr/bin/python3
import os
import subprocess
import json
import warnings
import urllib.parse
import urllib.request
import collections

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
            f.write(f"[ORCL]\n"+arguments)


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




def setuser(args):
    try:
        import psycopg2
        from psycopg2 import connect, extensions, sql


        NewUser = collections.namedtuple('NewUser', 'username password')

        users = [
            NewUser(args.username, args.password)
        ]

        with psycopg2.connect(dbname=args.db, user=args.superuser, password=args.superpass, host=args.host, port=args.port) as conn:
            cur: psycopg2.extensions.cursor = conn.cursor()
            for user in users:
                cur.execute(
                    sql.SQL("create user {username} with password %s")
                    .format(username=sql.Identifier(user.username)), 
                    (user.password, )
                )
            conn.commit()

        return True

    except Exception as e:
        print(str(e))
        return False


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

    py_file_url=plugin_url+"/"+plugin_name+".py"
    cfg_file_url=plugin_url+"/"+plugin_name+".cfg"
    if not download_file(py_file_url, temp_plugin_path):return False
    if not download_file(cfg_file_url, temp_plugin_path):return False
    return True


def execute_command(cmd, need_out=False):
    try:
        if not isinstance(cmd, list):
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
            print(f"    Unable to create {path} Directory  : {str(e)}")
            return False
    return True


def check_directory(path):
    return os.path.isdir(path)

def initiate(plugin_name, plugin_url, args):
    print(" ")
    print("------------------------------ Starting Plugin Automation ------------------------------")
    print()

    #Installing psycopg2 python module
    print("    Installing psycopg2 python module")
    psycopg2_choice=input("    Do you want to continue? [Y/n]")
    if psycopg2_choice=="Y" or psycopg2_choice=="y":
        cmd="""pip3 install psycopg2-binary"""
        if not execute_command(cmd):
            print("")
            print("------------------------------ Plugin Automation Failed ------------------------------")
            return 
        print("    Installed psycopg2-binary python module")
        print()
    else:
        print("    psycopg2-binary not installed")
        print("------------------------------ Plugin Automation Failed ------------------------------")
        return

    agent_path="/opt/site24x7/monagent/"
    agent_temp_path=agent_path+"temp/"
    agent_plugin_path=agent_path+"plugins/"

    if not check_directory(agent_temp_path):
        print("    Agent Directory does not Exist")
        print("------------------------------ Plugin Automation Failed ------------------------------")
        return
    print("    Creating Temporary Plugins Directory")
    plugins_temp_path=os.path.join(agent_temp_path,"plugins/")
    if not check_directory(plugins_temp_path):
        if not make_directory(plugins_temp_path):
            print("")
            print("------------------------------ Plugin Automation Failed ------------------------------")
            return 
    print("    Created Temporary Plugins Directory")
    print()

    print("    Downloading Postgres Plugin Files")
    postgres_file_choice=input("    Do you want to continue? [Y/n]")
    if postgres_file_choice=="Y" or postgres_file_choice=="y":

        if not down_move(plugin_name, plugin_url, plugins_temp_path):
            print("")
            print("------------------------------ Plugin Automation Failed ------------------------------")
            return 
        print("    Downloaded Postgres Plugin Files")
        print()

    else:
        print("   Postgres Files not Downloaded")
        print("------------------------------ Plugin Automation Failed ------------------------------")
        return

    print("    Setting the python3 path in the postgres.py file")
    print()

    py_update_cmd = [ "sed", "-i", "1s|^.*|#! /usr/bin/python3|", f"{plugins_temp_path}{plugin_name}/{plugin_name}.py" ]
    if not execute_command(py_update_cmd):
        print("------------------------------ Plugin Automation Failed ------------------------------")
        return 

    print(f"    Setting the Postgres User \"{args.username}\" for Plugin Execution")
    user_choice=input("    Do you want to continue? [Y/n]")
    if user_choice =="Y" or user_choice=="y":

        if not setuser(args):
            print("")
            print("------------------------------ Plugin Automation Failed ------------------------------")
            return 
        print(f"    \"{args.username}\" User created Successfully")
        print("")
    
    else:
        print(" User creation \"{args.username}\" failed")
        print("------------------------------ Plugin Automation Failed ------------------------------")


    print("    Creating executable plugin file")
    cmd=f"chmod 744 {plugins_temp_path}/{plugin_name}/{plugin_name}.py"
    if not execute_command(cmd):
        print("")
        print("------------------------------ Plugin Automation Failed ------------------------------")
        return 
    print("    Created executable plugin file")
    print("")

    print("    Validating the python plugin output")
    port=int(args.port)
    arguments=f"--host={args.host} --port={port} --username={args.username} --password={args.password} --db={args.db}"
    cmd=f"{plugins_temp_path}{plugin_name}/{plugin_name}.py"+ " "+arguments
    result=execute_command(cmd, need_out=True)
    if not plugin_validator(result):
        print("")
        print("------------------------------ Plugin Automation Failed ------------------------------")
        return
    print("    Plugin output validated successfully")
    print("")

    print("    Setting plugin configuration")
    if not plugin_config_setter(plugin_name, plugins_temp_path, arguments):
        print("")
        print("------------------------------ Plugin Automation Failed ------------------------------")
        return 
    print("    Plugin configuration set sucessfully")
    print()

    print("    Moving the plugin into the Site24x7 Agent directory")
    if not move_plugin(plugin_name, plugins_temp_path, agent_plugin_path):
        print("")
        print("------------------------------ Plugin Automation Failed ------------------------------")
        return 
    print("    Moved the plugin into the Site24x7 Agent directory")
    print()


    print("------------------------------ Successfully Completed Plugin Automation ------------------------------")



if __name__ == "__main__":
    plugin_name="postgres"
    plugin_url="https://raw.githubusercontent.com/site24x7/plugins/master/postgres"

    #user configs
    superuser="suraj_sys"
    superpass="suraj_sys"
    host="localhost"
    port=5432
    username="suraj"
    password="suraj"
    db="postgres"

    superuser=input("\n Enter the Super User of the Postgres Instance : ")
    if not superuser: print("No Super User Entered");exit()

    superpass=input("\n Enter the Password of the Postgres Instance : ")
    if not superpass: print("No Super User Password Entered");exit()

    username=input("\n Enter the Username to be created in the Postgres Instance : ") or "site24x7_plugin"
    if not username: print("No Username Entered, using default user \"site24x7_plugin\"")

    password=input(f"\n Enter the password for the user \'{username}\' to be created in the Postgres Instance : ")
    if not password: print("No password Entered");exit()

    host=input("\n Enter the hostname where the Postgres Instance is running (default option: \"localhost\") : ") or "localhost"

    port=input("\n Enter the port where the Postgres Instance is running (dafault option: \"5432\"): ") or "5432"
    db=input("\n Enter the database to which the plugin has to be connected (dafault option: \"postgres\"): ") or "postgres"



    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--superuser', help='hostname for postgres',default=superuser)
    parser.add_argument('--superpass', help='hostname for postgres',default=superpass)
    parser.add_argument('--username', help='username for postgres',default=username)
    parser.add_argument('--password', help='password for postgres',default=password)
    parser.add_argument('--host', help='hostname for postgres',default=host)
    parser.add_argument('--port', help='port number for postgres',default=port)
    parser.add_argument('--db', help='DB for postgres',default=db)
    parser.add_argument('--plugin_version', help='plugin template version', type=int,  nargs='?', default=1)
    parser.add_argument('--heartbeat', help='alert if monitor does not send data', type=bool, nargs='?', default=True)

    args=parser.parse_args()

    initiate(plugin_name, plugin_url, args)