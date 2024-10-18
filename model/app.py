from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates
import google.generativeai as genai
import matplotlib.pyplot as plt
import io
import os
import sys
import traceback
import re
import html

app = FastAPI()

templates = Jinja2Templates(directory="templates")

model = genai.GenerativeModel("gemini-1.5-flash")

# to store output images
output_dir = "static/images"
os.makedirs(output_dir, exist_ok=True)

@app.get("/", response_class=HTMLResponse)
async def get_form(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/generate", response_class=HTMLResponse)
async def generate_code(request: Request, prompt: str = Form(...)):
    response = model.generate_content(prompt)
    generated_code = response.text

    # extract python code
    code_match = re.search(r"```(?:python)?\n(.*?)```", generated_code, re.DOTALL)
    if code_match:
        extracted_code = code_match.group(1).strip()
    else:
        extracted_code = generated_code

    # Decode HTML entities like &#x27;
    extracted_code = html.unescape(extracted_code)
    generated_code_escaped = html.escape(extracted_code)

    return templates.TemplateResponse("index.html", {
        "request": request,
        "prompt": prompt,
        "generated_code": extracted_code
    })


@app.post("/execute", response_class=HTMLResponse)
async def execute_code(request: Request, generated_code: str = Form(...)):
    output_image_path = None
    plt_file = os.path.join(output_dir, "output.png")
    execution_result = None

    # buffer to capture print output
    output_buffer = io.StringIO()

    try:
        sys.stdout = output_buffer

        # environment for executing the code safely
        local_env = {
            "plt": plt,  # matplotlib.pyplot for plotting
            "__builtins__": __builtins__,  # built-in functions
        }
        exec(generated_code, local_env)

        # capture any printed output
        execution_result = output_buffer.getvalue()

        # save generated figure, if any
        if plt.get_fignums():
            plt.savefig(plt_file)
            plt.close()
            output_image_path = plt_file
        else:
            if not execution_result:
                execution_result = "Code executed successfully, but no output generated."

    except Exception as e:
        execution_result = f"Error executing the code:\n{traceback.format_exc()}"

    finally:
        sys.stdout = sys.__stdout__

    return templates.TemplateResponse("index.html", {
        "request": request,
        "generated_code": generated_code,
        "execution_result": execution_result,
        "output_image_path": output_image_path
    })


# route to serve images
@app.get("/static/images/{image_name}", response_class=FileResponse)
async def get_image(image_name: str):
    image_path = os.path.join(output_dir, image_name)
    return FileResponse(image_path)
