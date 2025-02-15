import requests
import json
import modules.scripts as scripts
import gradio as gr
from modules import script_callbacks
import time
import threading
import urllib.request
import urllib.parse
import urllib.error
import os
from tqdm import tqdm
import re
from requests.exceptions import ConnectionError
import urllib.request
from modules.shared import opts, cmd_opts
from modules.paths import models_path
import shutil
from html import escape

def download_file(url, file_name):
    # Maximum number of retries
    max_retries = 5

    # Delay between retries (in seconds)
    retry_delay = 10

    while True:
        # Check if the file has already been partially downloaded
        if os.path.exists(file_name):
            # Get the size of the downloaded file
            downloaded_size = os.path.getsize(file_name)

            # Set the range of the request to start from the current size of the downloaded file
            headers = {"Range": f"bytes={downloaded_size}-"}
        else:
            downloaded_size = 0
            headers = {}

        # Split filename from included path
        tokens = re.split(re.escape('\\'), file_name)
        file_name_display = tokens[-1]

        # Initialize the progress bar
        progress = tqdm(total=1000000000, unit="B", unit_scale=True, desc=f"Downloading {file_name_display}", initial=downloaded_size, leave=False)

        # Open a local file to save the download
        global isDownloading
        with open(file_name, "ab") as f:
            while isDownloading:
                try:
                    # Send a GET request to the URL and save the response to the local file
                    response = requests.get(url, headers=headers, stream=True)

                    # Get the total size of the file
                    total_size = int(response.headers.get("Content-Length", 0))

                    # Update the total size of the progress bar if the `Content-Length` header is present
                    if total_size == 0:
                        total_size = downloaded_size
                    progress.total = total_size 

                    # Write the response to the local file and update the progress bar
                    for chunk in response.iter_content(chunk_size=1024):
                        if chunk:  # filter out keep-alive new chunks
                            f.write(chunk)
                            progress.update(len(chunk))
                        if (isDownloading == False):
                            response.close
                            break
                    downloaded_size = os.path.getsize(file_name)
                    # Break out of the loop if the download is successful
                    break
                except ConnectionError as e:
                    # Decrement the number of retries
                    max_retries -= 1

                    # If there are no more retries, raise the exception
                    if max_retries == 0:
                        raise e

                    # Wait for the specified delay before retrying
                    time.sleep(retry_delay)

        # Close the progress bar
        progress.close()
        if (isDownloading == False):
            print (f'Canceled!')
            break
        isDownloading = False
        downloaded_size = os.path.getsize(file_name)
        # Check if the download was successful
        if downloaded_size >= total_size:
            print(f"Downloaded: {file_name_display}")
            break
        else:
            print(f"Error: File download failed. Retrying... {file_name_display}")

#def download_file(url, file_name):
#    # Download the file and save it to a local file
#    response = requests.get(url, stream=True)
#
#    # Get the total size of the file
#    total_size = int(response.headers.get("Content-Length", 0))
#
#    # Split filename from included path
#    tokens = re.split(re.escape('\\'), file_name)
#    file_name_display = tokens[-1]
#
#    # Initialize the progress bar
#    progress = tqdm(total=total_size, unit="B", unit_scale=True, desc=f"Downloading {file_name_display}")
#
#    # Open a local file to save the download
#    with open(file_name, "wb") as f:
#        # Iterate over the response chunks and update the progress bar
#        for chunk in response.iter_content(chunk_size=1024):
#            if chunk:  # filter out keep-alive new chunks
#                f.write(chunk)
#                progress.update(len(chunk))
#
#    # Close the progress bar
#    progress.close()
def contenttype_folder(content_type):
    if content_type == "Checkpoint":
        if cmd_opts.ckpt_dir:
            folder = cmd_opts.ckpt_dir #"models/Stable-diffusion"
        else:            
            folder = os.path.join(models_path,"Stable-diffusion") 
        new_folder = os.path.join(folder,"new") #"models/Stable-diffusion/new"
    elif content_type == "Hypernetwork":
        folder = cmd_opts.hypernetwork_dir #"models/hypernetworks"
        new_folder = os.path.join(folder,"new") #"models/hypernetworks/new"
    elif content_type == "TextualInversion":
        folder = cmd_opts.embeddings_dir #"embeddings"
        new_folder = os.path.join(folder,"new") #"embeddings/new"
    elif content_type == "AestheticGradient":
        folder = "extensions/stable-diffusion-webui-aesthetic-gradients/aesthetic_embeddings"
        new_folder = "extensions/stable-diffusion-webui-aesthetic-gradients/aesthetic_embeddings/new"
    elif content_type == "LORA":
        folder = cmd_opts.lora_dir #"models/Lora"
        new_folder = os.path.join(folder,"new") #"models/Lora/new"
    elif content_type == "LoCon":
        if "lyco_dir" in cmd_opts:
            folder = f"{cmd_opts.lyco_dir}"
        elif "lyco_dir_backcompat" in cmd_opts: #A1111 V1.5.1
            folder = f"{cmd_opts.lyco_dir_backcompat}"
        else:
            folder = os.path.join(models_path,"LyCORIS")
        new_folder = os.path.join(folder,"new") #"models/Lora/new"
    elif content_type == "VAE":
        if cmd_opts.vae_dir:
            folder = cmd_opts.vae_dir #"models/VAE"
        else:
            folder = os.path.join(models_path,"VAE")
        new_folder = os.path.join(folder,"new") #"models/VAE/new"
    elif content_type == "Controlnet":
        if cmd_opts.ckpt_dir:
            folder = os.path.join(os.path.join(cmd_opts.ckpt_dir, os.pardir), "ControlNet")
        else:            
            folder = os.path.join(models_path,"ControlNet")
        new_folder = os.path.join(folder,"new") 
    elif content_type == "Poses":
        if cmd_opts.ckpt_dir:
            folder = os.path.join(os.path.join(cmd_opts.ckpt_dir, os.pardir), "Poses")
        else:            
            folder = os.path.join(models_path,"Poses")
        new_folder = os.path.join(folder,"new") 
    return folder, new_folder

def escaped_modelpath(folder, model_name):
    escapechars = str.maketrans({" ": r"_",
                                     "(": r"",
                                     ")": r"",
                                     "|": r"",
                                     ":": r"",
                                     ",": r"_",
                                     "<": r"",
                                     ">": r"",
                                     "!": r"",
                                     "?": r"",
                                     ".": r"_",
                                     "&": r"_and_",
                                     "*": r"_",
                                     "\"": r"",
                                     "\\": r""})
    return os.path.join(folder,model_name.translate(escapechars))

def extranetwork_folder(content_type, use_new_folder, model_name:str = "",base_model:str="", make_dir:bool=True):
    folder, new_folder = contenttype_folder(content_type)
    if use_new_folder:
        #model_folder = os.path.join(new_folder,model_name.replace(" ","_").replace("(","").replace(")","").replace("|","").replace(":","-").replace(",","_").replace("\\",""))
        model_folder = escaped_modelpath(new_folder, model_name)
        if not os.path.exists(new_folder):
            if make_dir: os.makedirs(new_folder)
        if not os.path.exists(model_folder):
            if make_dir: os.makedirs(model_folder)
        
    else:
        #model_folder = os.path.join(folder,model_name.replace(" ","_").replace("(","").replace(")","").replace("|","").replace(":","-").replace(",","_").replace("\\",""))
        if not 'SD 1' in base_model:
            folder = os.path.join(folder, '_' + base_model.replace(' ','_').replace('.','_'))
        model_folder = escaped_modelpath(folder, model_name)
        if not os.path.exists(model_folder):
            if make_dir: os.makedirs(model_folder)
    #print(f"Folder Path:{model_folder}")
    return model_folder

def download_file_thread(url, file_name, content_type, use_new_folder, model_name,base_model):
    global isDownloading
    if isDownloading:
        isDownloading = False
        return
    isDownloading = True
    model_folder = extranetwork_folder(content_type, use_new_folder,model_name,base_model)
    path_to_new_file = os.path.join(model_folder, file_name)     

    thread = threading.Thread(target=download_file, args=(url, path_to_new_file))

        # Start the thread
    thread.start()

def save_text_file(file_name, content_type, use_new_folder, trained_words, model_name, base_model):
    model_folder = extranetwork_folder(content_type, use_new_folder, model_name,base_model)   
    path_to_new_file = os.path.join(model_folder, file_name.replace(".ckpt",".txt").replace(".safetensors",".txt").replace(".pt",".txt").replace(".yaml",".txt").replace(".zip",".txt"))
    print(f"{path_to_new_file}")
    if not os.path.exists(path_to_new_file):
        with open(path_to_new_file, 'w') as f:
            f.write(trained_words)

# Set the URL for the API endpoint
api_url = "https://civitai.com/api/v1/models?limit=10"
json_data = None
json_info = None
isDownloading = False

def api_to_data(content_type, sort_type, use_search_term, search_term=None):
    query = {'types': content_type, 'sort': sort_type}
    if use_search_term != "No" and search_term:
        #search_term = search_term.replace(" ","%20")
        match use_search_term:
            case "User name":
                query |= {'username': search_term }
            case "Tag":
                query |= {'tag': search_term }
            case _:
                query |= {'query': search_term }
    return request_civit_api(f"{api_url}", query )

def api_next_page(next_page_url=None):
    global json_data
    if next_page_url is None:
        try: json_data['metadata']['nextPage']
        except: return
        next_page_url = json_data['metadata']['nextPage']
    return request_civit_api(next_page_url)

def model_list_html(json_data, model_dict, content_type):
    allownsfw = json_data['allownsfw']
    HTML = '<div class="column civmodellist">'
    for item in json_data['items']:
        for k,model in model_dict.items():
            if model_dict[k] == item['name']:
                #print(f'Item:{item["modelVersions"][0]["images"]}')
                model_name = escape(item["name"].replace("'","\\'"),quote=True)
                #print(f'{model_name}')
                #print(f'Length: {len(item["modelVersions"][0]["images"])}')
                nsfw = ""
                alreadyhave = ""
                if any(item['modelVersions']):
                    if len(item['modelVersions'][0]['images']) > 0:
                        if item["modelVersions"][0]["images"][0]['nsfw'] != "None" and not allownsfw:
                            nsfw = 'civcardnsfw'
                        imgtag = f'<img src={item["modelVersions"][0]["images"][0]["url"]}"></img>'
                    else:
                        imgtag = f'<img src="./file=html/card-no-preview.png"></img>'
                        
                    for file in item['modelVersions'][0]['files']:
                        file_name = file['name']
                        base_model = item["modelVersions"][0]['baseModel']
                        folder = extranetwork_folder(content_type,False,item["name"],base_model, False)
                        path_file = os.path.join(folder, file_name)
                        #print(f"{path_file}")
                        if os.path.exists(path_file):
                            alreadyhave = "civmodelcardalreadyhave"
                            break
                HTML = HTML +  f'<figure class="civmodelcard {nsfw} {alreadyhave}" onclick="select_model(\'{model_name}\')">'\
                                +  imgtag \
                                +  f'<figcaption>{item["name"]}</figcaption></figure>'
    HTML = HTML + '</div>'
    return HTML

def update_prev_page(show_nsfw, content_type):
    return update_next_page(show_nsfw, content_type, False)

def update_next_page(show_nsfw, content_type, isNext=True, ):
    global json_data
    if isNext:
        json_data = api_next_page()
    else:
        if json_data['metadata']['prevPage'] is not None:
            json_data = api_next_page(json_data['metadata']['prevPage'])
        else:
            json_data = None
    if json_data is None:
        return
    json_data['allownsfw'] = show_nsfw # Add key for nsfw
    (hasPrev, hasNext, pages) = pagecontrol(json_data)
    model_dict = {}
    try:
        json_data['items']
    except TypeError:
        return gr.Dropdown.update(choices=[], value=None)

    for item in json_data['items']:
        temp_nsfw = item['nsfw']
        if (not temp_nsfw or show_nsfw):
            model_dict[item['name']] = item['name']
    HTML = model_list_html(json_data, model_dict, content_type)
    return  gr.Dropdown.update(choices=[v for k, v in model_dict.items()], value=None),\
            gr.Dropdown.update(choices=[], value=None),\
            gr.HTML.update(value=HTML),\
            gr.Button.update(interactive=hasPrev),\
            gr.Button.update(interactive=hasNext),\
            gr.Textbox.update(value=pages)

def pagecontrol(json_data):
    pages = f"{json_data['metadata']['currentPage']}/{json_data['metadata']['totalPages']}"
    hasNext = False
    hasPrev = False
    if 'nextPage' in json_data['metadata']:
        hasNext = True
    if 'prevPage' in json_data['metadata']:
        hasPrev = True
    return hasPrev,hasNext,pages

def update_model_list(content_type, sort_type, use_search_term, search_term, show_nsfw):
    global json_data
    json_data = api_to_data(content_type, sort_type, use_search_term, search_term)
    if json_data is None:
        return
    json_data['allownsfw'] = show_nsfw # Add key for nsfw
    (hasPrev, hasNext, pages) = pagecontrol(json_data)
    model_dict = {}
    for item in json_data['items']:
        temp_nsfw = item['nsfw']
        if (not temp_nsfw or show_nsfw):
            model_dict[item['name']] = item['name']
    HTML = model_list_html(json_data, model_dict, content_type)
    return  gr.Dropdown.update(choices=[v for k, v in model_dict.items()], value=None),\
            gr.Dropdown.update(choices=[], value=None),\
            gr.HTML.update(value=HTML),\
            gr.Button.update(interactive=hasPrev),\
            gr.Button.update(interactive=hasNext),\
            gr.Textbox.update(value=pages)

def update_model_versions(model_name=None):
    if model_name is not None:
        global json_data
        versions_dict = {}
        for item in json_data['items']:
            if item['name'] == model_name:
                for model in item['modelVersions']:
                    versions_dict[model['name']] = item["name"]
        return gr.Dropdown.update(choices=[k for k, v in versions_dict.items()], value=f'{next(iter(versions_dict.keys()), None)}')
    else:
        return gr.Dropdown.update(choices=[], value=None)

def update_dl_url(model_name=None, model_version=None, model_filename=None):
    if model_filename:
        global json_data
        dl_dict = {}
        dl_url = None
        #model_version = model_version.replace(f' - {model_name}','').strip()
        for item in json_data['items']:
            if item['name'] == model_name:
                for model in item['modelVersions']:
                    if model['name'] == model_version:
                        for file in model['files']:
                            if file['name'] == model_filename:
                                dl_url = file['downloadUrl']
                                global json_info
                                json_info = model
        return gr.Textbox.update(value=dl_url)
    else:
        return gr.Textbox.update(value=None)

def  update_model_info(model_name=None, model_version=None):
    if model_name and model_version:
        #model_version = model_version.replace(f' - {model_name}','').strip()
        global json_data
        output_html = ""
        output_training = ""
        output_basemodel = ""
        img_html = ""
        model_desc = ""
        dl_dict = {}
        allow = {}
        allownsfw = json_data['allownsfw']
        for item in json_data['items']:
            if item['name'] == model_name:
                model_uploader = item['creator']['username']
                tags = item['tags']
                if item['description']:
                    model_desc = item['description']
                if item['allowNoCredit']:
                    allow['allowNoCredit'] = item['allowNoCredit']
                if item['allowCommercialUse']:
                    allow['allowCommercialUse'] = item['allowCommercialUse']
                if item['allowDerivatives']:
                    allow['allowDerivatives'] = item['allowDerivatives']
                if item['allowDifferentLicense']:
                    allow['allowDifferentLicense'] = item['allowDifferentLicense']
                for model in item['modelVersions']:
                    if model['name'] == model_version:
                        if model['trainedWords']:
                            output_training = ", ".join(model['trainedWords'])
                        if model['baseModel']:
                            output_basemodel = model['baseModel']
                        for file in model['files']:
                            dl_dict[file['name']] = file['downloadUrl']

                        model_url = model['downloadUrl']
                        #model_filename = model['files']['name']

                        img_html = '<div class="sampleimgs">'
                        for pic in model['images']:
                            nsfw = None
                            if pic['nsfw'] != "None" and not allownsfw:
                                nsfw = 'class="civnsfw"'
                            img_html = img_html + f'<div {nsfw} style="display:flex;align-items:flex-start;"><img src={pic["url"]} style="width:20em;"></img>'
                            if pic['meta']:
                                img_html = img_html + '<div style="text-align:left;line-height: 1.5em;">'
                                for key, value in pic['meta'].items():
                                    img_html = img_html + f'{escape(str(key))}: {escape(str(value))}</br>'
                                img_html = img_html + '</div>'
                            img_html = img_html + '</div>'
                        img_html = img_html + '</div>'
                        output_html = f"<p><b>Model</b>: {escape(str(model_name))}<br><b>Version</b>: {escape(str(model_version))}<br><b>Uploaded by</b>: {escape(str(model_uploader))}<br><b>Base Model</b>: {escape(str(output_basemodel))}</br><b>Tags</b>: {escape(str(tags))}<br><b>Trained Tags</b>: {escape(str(output_training))}<br>{escape(str(allow))}<br><a href={model_url}><b>Download Here</b></a></p><br><br>{model_desc}<br><div align=center>{img_html}</div>"
                
        return  gr.HTML.update(value=output_html),\
                gr.Textbox.update(value=output_training),\
                gr.Dropdown.update(choices=[k for k, v in dl_dict.items()], value=next(iter(dl_dict.keys()), None)),\
                gr.Textbox.update(value=output_basemodel)
    else:
        return  gr.HTML.update(value=None),\
                gr.Textbox.update(value=None),\
                gr.Dropdown.update(choices=[], value=None),\
                gr.Textbox.update(value='')


def request_civit_api(api_url=None, payload=None):
    if payload is not None:
        payload = urllib.parse.urlencode(payload, quote_via=urllib.parse.quote)
    # Make a GET request to the API
    try:
        response = requests.get(api_url, params=payload, timeout=(10,15))
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print("Request error: ", e)
        #print(f"Query: {payload} URL: {response.url}")
        exit() #return None
    else:
        response.encoding  = "utf-8" # response.apparent_encoding
        data = json.loads(response.text)
    # Check the status code of the response
    #if response.status_code != 200:
    #  print("Request failed with status code: {}".format(response.status_code))
    #  exit()
    return data


def update_everything(list_models, list_versions, dl_url):
    (a, d, f, base_model) = update_model_info(list_models, list_versions)
    dl_url = update_dl_url(list_models, list_versions, f['value'])
    return (a, d, f, list_versions, list_models, dl_url, base_model)

def save_image_files(preview_image_html, model_filename, list_models, content_type, use_new_folder,base_model):
    print("Save Images Clicked")

    model_folder = extranetwork_folder(content_type, use_new_folder, list_models, base_model)
    img_urls = re.findall(r'src=[\'"]?([^\'" >]+)', preview_image_html)
    
    name = os.path.splitext(model_filename)[0]
    #model_folder = os.path.join("models\Stable-diffusion",list_models.replace(" ","_").replace("(","").replace(")","").replace("|","").replace(":","-"))

    opener = urllib.request.build_opener()
    opener.addheaders = [('User-agent', 'Mozilla/5.0')]
    urllib.request.install_opener(opener)

    HTML = preview_image_html
    for i, img_url in enumerate(img_urls):
        filename = f'{name}_{i}.png'
        filenamethumb = f'{name}.png'
        if content_type == "TextualInversion":
            filename = f'{name}_{i}.preview.png'
            filenamethumb = f'{name}.preview.png'
        HTML = HTML.replace(img_url,f'"{filename}"')
        img_url = urllib.parse.quote(img_url,  safe=':/=')   #img_url.replace("https", "http").replace("=","%3D")
        print(img_url, model_folder, filename)
        try:
            with urllib.request.urlopen(img_url) as url:
                with open(os.path.join(model_folder, filename), 'wb') as f:
                    f.write(url.read())
                    if i == 0 and not os.path.exists(os.path.join(model_folder, filenamethumb)):
                        shutil.copy2(os.path.join(model_folder, filename),os.path.join(model_folder, filenamethumb))
                    print("\t\t\tDownloaded")
            #with urllib.request.urlretrieve(img_url, os.path.join(model_folder, filename)) as dl:
                    
        except urllib.error.URLError as e:
            print(f'Error: {e.reason}')
    path_to_new_file = os.path.join(model_folder, f'{name}.html')
    #if not os.path.exists(path_to_new_file):
    with open(path_to_new_file, 'wb') as f:
        f.write(HTML.encode('utf8'))
    #Save json_info
    path_to_new_file = os.path.join(model_folder, f'{name}.civitai.info')
    with open(path_to_new_file, mode="w", encoding="utf-8") as f:
        json.dump(json_info, f, indent=2, ensure_ascii=False)

    print(f"Done.")
   
def on_ui_tabs():
    with gr.Blocks() as civitai_interface:
        with gr.Row():
            with gr.Column(scale=2):
                content_type = gr.Radio(label='Content type:', choices=["Checkpoint","TextualInversion","LORA","LoCon","Poses","Controlnet","Hypernetwork","AestheticGradient", "VAE"], value="Checkpoint", type="value")
            with gr.Column(scale=1,min_width=100):
                    sort_type = gr.Dropdown(label='Sort List by:', choices=["Newest","Most Downloaded","Highest Rated","Most Liked"], value="Newest", type="value")
                    show_nsfw = gr.Checkbox(label="NSFW content", value=False)
        with gr.Row():
            use_search_term = gr.Radio(label="Search", choices=["No", "Model name", "User name", "Tag"],value="No")
            search_term = gr.Textbox(label="Search Term", interactive=True, lines=1)
        with gr.Row():
            with gr.Column(scale=4):
                get_list_from_api = gr.Button(label="Get List", value="Get List")
            with gr.Column(scale=2,min_width=80):
                get_prev_page = gr.Button(value="Prev. Page")
            with gr.Column(scale=2,min_width=80):
                get_next_page = gr.Button(value="Next Page")
            with gr.Column(scale=1,min_width=80):
                pages = gr.Textbox(label='Pages',show_label=False)
        with gr.Row():
            list_html = gr.HTML()
        with gr.Row():
            list_models = gr.Dropdown(label="Model", choices=[], interactive=True, elem_id="quicksettings1", value=None)
            event_text = gr.Textbox(label="Event text",elem_id="eventtext1", visible=False, interactive=True, lines=1)
            list_versions = gr.Dropdown(label="Version", choices=[], interactive=True, elem_id="quicksettings", value=None)
        with gr.Row():
            txt_list = ""
            dummy = gr.Textbox(label='Trained Tags (if any)', value=f'{txt_list}', interactive=True, lines=1)
            base_model = gr.Textbox(label='Base Model', value='', interactive=True, lines=1)
            model_filename = gr.Dropdown(label="Model Filename", choices=[], interactive=True, value=None)
            dl_url = gr.Textbox(label="Download Url", interactive=False, value=None)
        with gr.Row():
            update_info = gr.Button(value='1st - Get Model Info')
            save_text = gr.Button(value="2nd - Save Text")
            save_images = gr.Button(value="3rd - Save Images")
            download_model = gr.Button(value="4th - Download Model")
            save_model_in_new = gr.Checkbox(label="Save Model to new folder", value=False)
        with gr.Row():
            preview_image_html = gr.HTML()

        save_text.click(
            fn=save_text_file,
            inputs=[
            model_filename,
            content_type,
            save_model_in_new,
            dummy,
            list_models,
            base_model
            ],
            outputs=[]
        )
        save_images.click(
            fn=save_image_files,
            inputs=[
            preview_image_html,
            model_filename,
            list_models,
            content_type,
            save_model_in_new,
            base_model
            ],
            outputs=[]
        )
        download_model.click(
            fn=download_file_thread,
            inputs=[
            dl_url,
            model_filename,
            content_type,
            save_model_in_new,
            list_models,
            base_model
            ],
            outputs=[]
        )
        get_list_from_api.click(
            fn=update_model_list,
            inputs=[
            content_type,
            sort_type,
            use_search_term,
            search_term,
            show_nsfw
            ],
            outputs=[
            list_models,
            list_versions,
            list_html,            
            get_prev_page,
            get_next_page,
            pages
            ]
        )
        update_info.click(
            fn=update_everything,
            #fn=update_model_info,
            inputs=[
            list_models,
            list_versions,
            dl_url
            ],
            outputs=[
            preview_image_html,
            dummy,
            model_filename,
            list_versions,
            list_models,
            dl_url,
            base_model
            ]
        )
        list_models.change(
            fn=update_model_versions,
            inputs=[
            list_models,
            ],
            outputs=[
            list_versions,
            ]
        )
        list_versions.change(
            fn=update_model_info,
            inputs=[
            list_models,
            list_versions,
            ],
            outputs=[
            preview_image_html,
            dummy,
            model_filename,
            base_model
            ]
        )
        model_filename.change(
            fn=update_dl_url,
            inputs=[list_models, list_versions, model_filename,],
            outputs=[dl_url,]
        )
        get_next_page.click(
            fn=update_next_page,
            inputs=[
            show_nsfw,
            content_type,
            ],
            outputs=[
            list_models,
            list_versions,
            list_html,
            get_prev_page,
            get_next_page,
            pages
            ]
        )
        get_prev_page.click(
            fn=update_prev_page,
            inputs=[
            show_nsfw,
            content_type,
            ],
            outputs=[
            list_models,
            list_versions,
            list_html,
            get_prev_page,
            get_next_page,
            pages
            ]
        )
        def update_models_dropdown(model_name):
            ret_versions=update_model_versions(model_name)
            (html,d, f, base_model) = update_model_info(model_name,ret_versions['value'])
            dl_url = update_dl_url(model_name, ret_versions['value'], f['value'])
            return gr.Dropdown.update(value=model_name),ret_versions ,html,dl_url,d,f,base_model
        event_text.change(
            fn=update_models_dropdown,
            inputs=[
                event_text,
            ],
            outputs=[
                list_models,
                list_versions,
                preview_image_html,
                dl_url,
                dummy,
                model_filename
            ]
        )

    return (civitai_interface, "CivitAi", "civitai_interface"),

script_callbacks.on_ui_tabs(on_ui_tabs)
