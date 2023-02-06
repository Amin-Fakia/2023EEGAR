from customtkinter import *
from threading import Thread
from DSI_to_Python_short import TCPParser
app = CTk()
app.geometry("700x300+900+400")
tcpParser = TCPParser('localhost',9067)
dsi_thread = Thread(target=tcpParser.start_data_processing)
dsi_thread.daemon = True
unity_thread = Thread(target=tcpParser.start_unity_connec)
unity_thread.daemon = True


checkBox_frame = CTkFrame(app)
check_vars = []
j = 0
i = 0
for idx,channel in enumerate(tcpParser.channels):
    check_vars.append(Variable())
    checkBox = CTkCheckBox(checkBox_frame,text=channel,variable=check_vars[idx])
    checkBox.select()
    checkBox.grid(row=j,column=i,padx=5,pady=5)
    if i == 4:
        i = 0
        j +=1
    else:
        i +=1
checkBox_frame.pack(padx=10,pady=10)

def check_channels():
    values = []
    for var in check_vars:
        values.append(var.get()==1)
    tcpParser.set_channels(values)

def startDSIThread():
    dsiBtn.configure(state=DISABLED)
    dsi_thread.start()

def startUnityThread():
    unityBtn.configure(state=DISABLED)
    unity_thread.start()

applyBtn = CTkButton(app,text="Apply",command=check_channels)
applyBtn.pack(padx=10,pady=10)

controlFrame = CTkFrame(app)
dsiBtn = CTkButton(controlFrame,text="Start DSI Connection",
                    command=startDSIThread,fg_color="#507963",hover_color='#3a4c40') # ,fg_color="#00ab41",hover_color='#008631'
unityBtn = CTkButton(controlFrame,text="Start Unity Connection",
                    command=startUnityThread,fg_color="#ff6600",hover_color='#853500')

dsiBtn.pack(side="left",padx=5,pady=5)
unityBtn.pack(side="left",padx=5,pady=5)
controlFrame.pack(padx=10,pady=10)
def on_closing():
    app.destroy()
    quit()



app.protocol("WM_DELETE_WINDOW", on_closing)
app.mainloop()