#! /usr/bin/python3
import os
import subprocess
import json
import warnings
import re
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

def check_user(user, c):
    try:
        query=f"SELECT * FROM dba_users WHERE username = \'{user.upper()}\'"
        cursor=execute_query(query, c, result=True)
        rows=cursor.fetchall()
        return len(rows)==1
    except Exception as e:
        print(str(e))
        return False


def close_cursor(c):
    try:
        c.close()
    except Exception as e:
        print(str(e))
        return False
    return True

def connect_cursor(username, password, dsn):
    try:
        import oracledb
        conn = oracledb.connect(user=username, password=password, dsn=dsn)
        c = conn.cursor()
        return c
    except Exception as e:
        print(str(e))
        return False

def execute_query(query, c, result=False):
    try:
        c.execute(query)
        if result:
            return c
    except Exception as e:
        print(str(e))
        return False
    return True


def setuser(args):
    try:
        dsn=f"{args.hostname}:{args.port}/{args.sid}"
        if args.tls==True:
            dsn=f"""(DESCRIPTION=
                    (ADDRESS=(PROTOCOL=tcps)(HOST={args.hostname})(PORT={args.port}))
                    (CONNECT_DATA=(SERVICE_NAME={args.sid}))
                    (SECURITY=(MY_WALLET_DIRECTORY={args.wallet_location}))
                    )"""

        c = connect_cursor(args.sysusername, args.syspassword, dsn)
        if not c:
            return False
        
        alter_session="""alter session set "_ORACLE_SCRIPT"=true"""
        create_query = f"CREATE USER {args.username} identified by {args.password}"
        query1 = f"GRANT SELECT_CATALOG_ROLE TO {args.username}"
        query2 = f"GRANT CREATE SESSION TO {args.username}"

        if not execute_query(alter_session, c): return False

        if check_user(args.username, c):
            print(f"   \"{args.username}\" User Already Exists")
            return False
        
        if not execute_query(create_query, c):return False

        if not close_cursor(c): return False
        
        c = connect_cursor(args.sysusername, args.syspassword, dsn)
        if not c:
            return False

        if not execute_query(query1, c): return False 
        if not execute_query(query2, c): return False 
        
        # Closing the oracle connection
        if not close_cursor(c): return False

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

    #Installing oracledb python module
    print("    Installing oracledb python module")
    oracledb_choice=input("    Do you want to continue? [Y/n]")
    if oracledb_choice=="Y" or oracledb_choice=="y":
        cmd="""pip3 install oracledb"""
        if not execute_command(cmd):
            print("")
            print("------------------------------ Plugin Automation Failed ------------------------------")
            return 
        print("    Installed oracledb python module")
        print()
    else:
        print("    oracledb not installed")
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

    print("    Downloading Oracle Plugin Files")
    oracle_file_choice=input("    Do you want to continue? [Y/n]")
    if oracle_file_choice=="Y" or oracle_file_choice=="y":

        if not down_move(plugin_name, plugin_url, plugins_temp_path):
            print("")
            print("------------------------------ Plugin Automation Failed ------------------------------")
            return 
        print("    Downloaded Oracle Plugin Files")
        print()

    else:
        print("   Oracle Files not Downloaded")
        print("------------------------------ Plugin Automation Failed ------------------------------")
        return

    print("    Setting the python3 path in the oracle.py file")

    py_update_cmd = [ "sed", "-i", "1s|^.*|#! /usr/bin/python3|", f"{plugins_temp_path}{plugin_name}/{plugin_name}.py" ]
    if not execute_command(py_update_cmd):
        print("------------------------------ Plugin Automation Failed ------------------------------")
        return 

    print(f"    Setting the Oracle User \"{args.username}\" for Plugin Execution")
    user_choice=input("    Do you want to continue? [Y/n]")
    if user_choice =="Y" or user_choice=="y":

        if not setuser(args):
            print("")
            print("------------------------------ Plugin Automation Failed ------------------------------")
            return 
        print(f"    \"{args.username}\" User created Successfully with Necessary Roles")
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
    arguments="--username={args.username} --password={args.password} --hostname={hostname} --sid={sid} --port={port} --tls={args.tls} --wallet_location={wallet_location} --oracle_home={oracle_home}"
    cmd=f"{plugins_temp_path}/{plugin_name}/{plugin_name}.py"+ " "+arguments
    result=execute_command(cmd, need_out=True)
    if not plugin_validator(result):
        print("")
        print("------------------------------ Plugin Automation Failed ------------------------------")
        return
    print("    Plugin output validated sucessfully")
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
    plugin_name="oracle"
    plugin_url="https://raw.githubusercontent.com/site24x7/plugins/master/oracle"

    #user configs
    sysusername = "suraj_sys"
    syspassword = "suraj_sys"
    username = "new_username"
    password = "new_password"
    sid = "ORCLCDB"
    hostname = "localhost"
    port = 1521
    tls="False"
    wallet_location = "/opt/oracle/product/19c/dbhome_1/wallet"
    oracle_home="/opt/oracle/product/19c/dbhome_1/"

    sysusername=input("\n Enter the Admin User of the Oracle Instance : ")
    if not sysusername: print("No Admin User Entered");exit()

    syspassword=input("\n Enter the Password of the Oracle Instance : ")
    if not syspassword: print("No Admin User Password Entered");exit()

    username=input("\n Enter the Username to be created in the Oracle Instance : ") or "site24x7_plugin"
    if not username: print("No Username Entered, using default user \"site24x7_plugin\"")

    password=input(f"\n Enter the password for the user \'{username}\' to be created in the Oracle Instance : ")
    if not password: print("No password Entered");exit()

    sid=input("\n Enter the SID of the Oracle Instance : ")
    if not sid: print("No SID Entered");exit()

    hostname=input("\n Enter the hostname where the Oracle Instance is running (default option: \"localhost\") : ") or "localhost"

    port=input("\n Enter the port where the Oracle Instance is running (dafault option: \"1521\"): ") or "1521"

    tls=input("\n Enter the TLS option (True/False) (default option: \"False\"): ") or "False"
    if tls=="True":
        wallet_location=input("\n Enter the wallet location : ") 
        if not wallet_location: print("Wallet location not entered"); exit()

    else:
        print("No TLS Entered, using default option \"False\"")
        wallet_location =None

    oracle_home=input("\n Enter the ORACLE_HOME location : ")
    if not oracle_home: print("No ORACLE_HOME Entered"); exit()


    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--sysusername', help='hostname for oracle',default=sysusername)
    parser.add_argument('--syspassword', help='hostname for oracle',default=syspassword)
    parser.add_argument('--username', help='username for oracle',default=username)
    parser.add_argument('--password', help='password for oracle',default=password)
    parser.add_argument('--sid', help='sid for oracle',default=sid)
    parser.add_argument('--hostname', help='hostname for oracle',default=hostname)
    parser.add_argument('--port', help='port number for oracle',default=port)
    parser.add_argument('--tls', help='tls support for oracle',default=tls)
    parser.add_argument('--wallet_location', help='oracle wallet location',default=wallet_location)
    parser.add_argument('--oracle_home', help='oracle wallet location',default=oracle_home)

    args=parser.parse_args()
    os.environ['ORACLE_HOME']=args.oracle_home

    initiate(plugin_name, plugin_url, args)