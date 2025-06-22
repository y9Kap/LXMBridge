from LXMKit.mu import *

logo = r"""
    ___                              _          ____       _     __         
   /   |_   _____  __  ______ _____ ( )_____   / __ )_____(_)___/ /___ ____ 
  / /| | | / / _ \\/ / / / __ '/ __ \\|// ___/  / __  / ___/ / __  / __ '/ _ \\
 / ___ | |/ /  __/ /_/ / /_/ / /_/ / (__  )  / /_/ / /  / / /_/ / /_/ /  __/
/_/  |_|___/\\___/\\__, /\\__, /\\____/ /____/  /_____/_/  /_/\\__,_/\\__, /\___/ 
                /____//____/                                   /____/       
"""

canvas = Micron(
    subnodes=[
        Div(
            subnodes = [
                Paragraph(logo, style=[FOREGROUND_LIGHT_GREY, CENTER]),
                Br(),
                Header(
                    content="What is this?",
                    subnodes=[
                        Paragraph("This is an experimental 'bridge' between the Meshtastic network in Sydney and LXM. When running, LXM clients can send messages to the mesh and vise-versa. See 5c16dcb8ccfaf6c8a85ff66aedb8f70d"),
                        Br(),
                    ]
                ),
                Br(),
                Header(
                    content="More info",
                    subnodes=[
                        Paragraph("You can read the source code (and more) once development finishes."),
                        Br(),
                    ]
                )

            ]
        )
    ]
)

if __name__ == "__main__":
    print(canvas.render())