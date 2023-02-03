from customtkinter import *
from DSI_to_Python_short import TCPParser
from threading import Thread
import matplotlib.pyplot as plt


class EEGApp(CTk):
    def __init__(self):
        super().__init__()
        self.geometry(f"{1400}x{780}")
        self.dsiTcp = TCPParser('localhost',9067,1)
        self.threadDSI = Thread(target=self.dsiTcp.start_data_processing)
        self.threadDSI.daemon = True
        self.unityThread = Thread(target=self.startUnity_Thread)
        self.unityThread.daemon = True

        ## CONTROL FRAME
        control_frame = CTkFrame(self,width=320)
        self.dsiBtn = CTkButton(control_frame,command=self.startDSI_Thread,text="Start DSI Thread")
        self.dsiBtn.pack(side="top",fill="x",padx=20,pady=20)
        self.unityBtn = CTkButton(control_frame,command=self.startUnity_Thread,text="Start Unity Thread",state=DISABLED)
        self.unityBtn.pack(side="top",fill="x",padx=20,pady=20)
        control_frame.pack(side="left",fill="y")


        main_frame = CTkFrame(self)
        ## DSI FRAME
        dsi_frame = CTkFrame(main_frame)
        dsi_frame.pack_propagate(0)
        self.info_dsi = CTkLabel(dsi_frame,wraplength=700,text="Test From DSI")
        self.info_dsi.pack(expand=True)
        dsi_frame.pack(fill="both",side="top",padx=10,pady=10)

        ## Unity FRAME
        unity_frame = CTkFrame(main_frame)
        unity_frame.pack_propagate(0)
        self.info_unity = CTkLabel(unity_frame,wraplength=700,text="Test From Unity")
        self.info_unity.pack(expand=True)
        dsi_frame.pack(fill="both",side="top",padx=10,pady=10)


        main_frame.pack(fill="both",expand=True,padx=10,pady=10)

    def update_dsiText(self):
        data = self.dsiTcp.log_dsi()
        ind = range(len(list(data.values())))
        # plt.cla()
        # plt.bar(ind,list(data.values()))
        # plt.xticks(ind,list(data.keys()))
        # plt.ylim((0,400000))
        # plt.show(block=False)
        # self.info_dsi.configure(text=str(self.dsiTcp.log_dsi()))
        self.info_dsi.after(60,self.update_dsiText)

    def startUnity_Thread(self):
        self.unityBtn.configure(state=DISABLED)
        self.unityThread.start()

    def startDSI_Thread(self):
        self.dsiBtn.configure(state=DISABLED)
        try:
            # self.tcp.start_data_parse()
            
            self.threadDSI.start()
            self.unityBtn.configure(state=NORMAL)
            self.update_dsiText()
        except Exception as e:
            # self.dsiBtn.configure(state=NORMAL)
            # self.unityBtn.configure(state=DISABLED)
            print(e)
            
        
    # def on_closing(self):
    #     self.dsiTcp.quit()
    #     quit()
        

        



if __name__ == "__main__":
    app = EEGApp()

    app.mainloop()
        