import gradio as gr
from cli import ask_rag

def chat(message, history):
    return ask_rag(message)

demo = gr.ChatInterface(
    fn=chat,
    title="Project Assistant",
    description="Internal Email Intelligence Search",
)

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
