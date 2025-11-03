import streamlit as st
import os
import re
import urllib.parse
import random
import time
from typing import List, Set, Tuple
import pandas as pd
import requests
from bs4 import BeautifulSoup
from ddgs import DDGS
import cloudscraper

# ---------------------------
# Configuração Inicial
# ---------------------------
st.set_page_config(
    page_title="Responde AI TOTVS",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------
# Configuração Selenium (Nova Adição)
# ---------------------------
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium.webdriver.chrome.service import Service
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    st.warning("Selenium não disponível. Instale: pip install selenium webdriver-manager")

# ---------------------------
# Headers Específicos para TOTVS
# ---------------------------
def get_totvs_specific_headers():
    return {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'Accept-Encoding': 'gzip, deflate, br',
        'Referer': 'https://centraldeatendimento.totvs.com/',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'same-origin',
        'Cache-Control': 'max-age=0',
        'X-Requested-With': 'XMLHttpRequest',
        'Origin': 'https://centraldeatendimento.totvs.com'
    }

# Lista de User-Agents alternativos
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36'
]

# Configuração melhorada do CloudScraper
def create_advanced_scraper():
    try:
        scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'mobile': False
            },
            delay=10,
            interpreter='nodejs'
        )
        return scraper
    except:
        return requests.Session()

scraper = create_advanced_scraper()

# ---------------------------
# Stop words e pré-processamento
# ---------------------------
STOP_WORDS = {
    "bom dia", "boa tarde", "boa noite", "olá", "att", "atenciosamente",
    "cumprimentos", "obrigado", "obrigada", "prezado", "prezada",
    "caro", "cara", "senhor", "senhora", "ola", "oi", "saudações",
    "tudo bem", "tudo bem?", "amigo", "amiga", "por favor",
    "grato", "grata", "cordialmente", "abraço", "abs"
}

def clean_query(query: str) -> str:
    if not query:
        return ""
    query = re.sub(r'[\u0080-\uFFFF]', '', query)
    query = query.lower().strip()
    for stop in STOP_WORDS:
        if query.startswith(stop):
            query = query[len(stop):].strip()
        if query.endswith(stop):
            query = query[:-len(stop)].strip()
    query = re.sub(r'[^\w\sáàâãéèêíïóôõöúçñ-]', ' ', query)
    query = re.sub(r'\s+', ' ', query).strip()
    parts = query.split()
    keep = []
    for p in parts:
        if len(p) >= 3 or p in ['erp', 'sql', 'api', 'xml', 'json', 'tss', 'nt', 'danfe']:
            keep.append(p)
    return " ".join(keep)

def clean_text(text: str) -> str:
    if not text or pd.isna(text):
        return ""
    text = text.replace("\0", " ")
    text = re.sub(r'Anexo\(s\):.*', '', text, flags=re.DOTALL)
    text = re.sub(r'<[^>]*>', ' ', text)
    text = re.sub(r'\\\w+', ' ', text)
    text = re.sub(r'\bhttps?://\S+\b', '', text)
    text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,7}\b', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def tem_video_ou_anexo(query: str) -> bool:
    padroes = [
        r"\banexo\b", r"\banexos\b", r"\banexado\b", r"\banexada\b",
        r"\bv[íi]deo\b", r"\bv[íi]deos\b", r"\bgravaç[ãa]o\b",
        r"\bprint\b", r"\bimagem\b", r"\bscreenshot\b"
    ]
    for p in padroes:
        if re.search(p, query.lower()):
            return True
    return False

# ---------------------------
# Sistema de Requisições Avançado
# ---------------------------
def fazer_requisicao_com_retry(url, max_tentativas=3):
    """Faz requisição com sistema de retry e múltiplas estratégias"""
    
    estrategias = [
        lambda: fazer_requisicao_cloudscraper(url),
        lambda: fazer_requisicao_requests(url),
    ]
    
    for tentativa in range(max_tentativas):
        for i, estrategia in enumerate(estrategias):
            try:
                response = estrategia()
                
                if response and response.status_code == 200:
                    return response
                    
                elif response and response.status_code == 403:
                    time.sleep(random.uniform(2, 5))
                    continue
                    
            except Exception:
                continue
                
        delay = min(2 ** tentativa, 30)
        time.sleep(delay + random.uniform(1, 3))
    
    return None

def fazer_requisicao_cloudscraper(url):
    """Tenta com CloudScraper primeiro"""
    headers = get_totvs_specific_headers()
    response = scraper.get(url, headers=headers, timeout=30)
    return response

def fazer_requisicao_requests(url):
    """Tenta com requests + headers"""
    session = requests.Session()
    headers = get_totvs_specific_headers()
    
    session.cookies.update({
        'ak_bmsc': 'simulated_cookie_value',
        'bm_sv': 'simulated_session_value'
    })
    
    response = session.get(url, headers=headers, timeout=30)
    return response

# ---------------------------
# Extração com Selenium (Nova)
# ---------------------------
def setup_selenium_driver():
    """Configura o driver do Selenium"""
    if not SELENIUM_AVAILABLE:
        return None
        
    try:
        chrome_options = Options()
        chrome_options.add_argument('--headless=new')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36')
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        return driver
    except Exception as e:
        st.error(f"Erro ao configurar Selenium: {e}")
        return None

def extrair_conteudo_com_selenium(url: str) -> str:
    """Usa Selenium para contornar proteções JavaScript"""
    if not SELENIUM_AVAILABLE:
        return "Selenium não disponível"
        
    driver = None
    try:
        driver = setup_selenium_driver()
        if not driver:
            return "Erro ao inicializar Selenium"
            
        driver.get(url)
        
        # Aguardar o conteúdo carregar
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Tentar encontrar conteúdo específico
        content_selectors = [
            "article",
            ".article-body",
            ".article-content", 
            "main",
            ".content",
            ".post-content"
        ]
        
        content = None
        for selector in content_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    content = elements[0]
                    break
            except:
                continue
        
        if content:
            texto = content.text
        else:
            texto = driver.find_element(By.TAG_NAME, "body").text
            
        return clean_text(texto)[:6000]
        
    except Exception as e:
        return f"Erro Selenium: {str(e)}"
    finally:
        if driver:
            driver.quit()

# ---------------------------
# Funções de Extração Híbridas
# ---------------------------
def extrair_id_artigo(url: str) -> str:
    """Extrai o ID do artigo da URL"""
    match = re.search(r'/articles/(\d+)', url)
    return match.group(1) if match else None

def processar_html_response(html_content: str) -> str:
    """Processa o HTML da TOTVS específico"""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Remover elementos específicos da TOTVS
    unwanted_elements = [
        'script', 'style', 'nav', 'footer', 'header', 
        'iframe', '.web-widget', '#mascara-org-suth'
    ]
    
    for element in unwanted_elements:
        for el in soup.select(element):
            el.decompose()
    
    # Buscar conteúdo principal
    content_selectors = [
        'article',
        '.article-body',
        '.article-content',
        'main',
        '.main-content',
        '[role="main"]'
    ]
    
    content = None
    for selector in content_selectors:
        content = soup.select_one(selector)
        if content:
            break
    
    if content:
        text = content.get_text(separator=' ', strip=True)
    else:
        text = soup.get_text(separator=' ', strip=True)
    
    return clean_text(text)[:6000]

def extrair_conteudo_pagina_avancado(url: str) -> str:
    """Estratégia híbrida para a Central Colaborativa TOTVS"""
    
    if '/search?' in url:
        return "Página de pesquisa - conteúdo não extraído"

    # Primeiro: tentar com abordagem direta
    try:
        headers = get_totvs_specific_headers()
        session = requests.Session()
        
        session.get('https://centraldeatendimento.totvs.com/', headers=headers, timeout=10)
        response = session.get(url, headers=headers, timeout=20)
        
        if response.status_code == 200:
            if 'access denied' not in response.text.lower() and 'blocked' not in response.text.lower():
                return processar_html_response(response.text)
    except:
        pass

    # Segundo: tentar API interna (se disponível)
    try:
        article_id = extrair_id_artigo(url)
        if article_id:
            api_url = f"https://centraldeatendimento.totvs.com/api/v2/help_center/pt-br/articles/{article_id}"
            headers = get_totvs_specific_headers()
            response = requests.get(api_url, headers=headers, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                if 'article' in data and 'body' in data['article']:
                    return clean_text(data['article']['body'])[:6000]
    except:
        pass

    return f"❌ Não foi possível acessar o conteúdo: {url}"

def extrair_conteudo_pagina(url: str) -> str:
    """Função principal de extração com múltiplas estratégias"""
    
    # Verificar se deve usar Selenium primeiro
    if st.session_state.get('usar_selenium', True) and SELENIUM_AVAILABLE:
        with st.spinner("🔄 Usando abordagem Selenium..."):
            conteudo = extrair_conteudo_com_selenium(url)
            if conteudo and not conteudo.startswith(("Erro", "Selenium não")):
                return conteudo
    
    # Fallback para métodos tradicionais
    with st.spinner("🔍 Tentando extração tradicional..."):
        return extrair_conteudo_pagina_avancado(url)

# ---------------------------
# Funções de Pesquisa
# ---------------------------
def pesquisar_interna_totvs(query: str, limit: int = 5) -> List[str]:
    """Pesquisa interna melhorada para a TOTVS"""
    base = "https://centraldeatendimento.totvs.com"
    search_url = f"{base}/hc/pt-br/search?query={urllib.parse.quote(query)}"
    
    links = []
    
    # Tentar com Selenium primeiro se disponível
    if SELENIUM_AVAILABLE and st.session_state.get('usar_selenium', True):
        try:
            driver = setup_selenium_driver()
            if driver:
                driver.get(search_url)
                
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='/articles/']"))
                )
                
                article_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/articles/']")
                for link in article_links:
                    href = link.get_attribute('href')
                    if href and href not in links:
                        links.append(href)
                    if len(links) >= limit:
                        break
                        
                driver.quit()
                return links
        except Exception as e:
            st.warning(f"Pesquisa Selenium falhou: {e}")
    
    # Fallback para pesquisa tradicional
    try:
        headers = get_totvs_specific_headers()
        response = fazer_requisicao_com_retry(search_url)
        
        if response and response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            for a in soup.select("a[href*='/articles/']"):
                href = a.get('href', '')
                if not href:
                    continue
                    
                if href.startswith('/'):
                    href = base + href
                elif not href.startswith('http'):
                    href = base + '/' + href.lstrip('/')
                    
                if href.startswith(base) and href not in links:
                    links.append(href)
                if len(links) >= limit:
                    break
    except Exception as e:
        st.error(f"Erro na pesquisa interna: {e}")
        
    return links

def buscar_documentacao_totvs(query: str, max_links: int = 5) -> List[str]:
    """Busca links na documentação TOTVS"""
    cleaned = clean_query(query) or query
    if "Protheus" not in cleaned.lower():
        search_query = f"site:centraldeatendimento.totvs.com Protheus {cleaned}"
    else:
        search_query = f"site:centraldeatendimento.totvs.com {cleaned}"
        
    found: List[str] = []
    seen: Set[str] = set()
    
    try:
        with DDGS() as ddgs:
            for r in ddgs.text(search_query, max_results=20):
                url = r.get("href", "")
                if url.startswith("https://centraldeatendimento.totvs.com") and "/articles/" in url:
                    if url not in seen:
                        found.append(url)
                        seen.add(url)
                if len(found) >= max_links:
                    break
    except Exception as e:
        st.error(f"Erro no DuckDuckGo: {e}")

    # Se não encontrou links suficientes, tentar pesquisa interna
    if len(found) < max_links:
        interna = pesquisar_interna_totvs(cleaned, limit=max_links)
        for url in interna:
            if url.startswith("https://centraldeatendimento.totvs.com") and url not in seen:
                found.append(url)
                seen.add(url)
            if len(found) >= max_links:
                break

    if not found:
        return [f"https://centraldeatendimento.totvs.com/hc/pt-br/search?query={urllib.parse.quote(cleaned)}"]

    return found[:max_links]

# ---------------------------
# Sistema de Relevância e IA
# ---------------------------
def pontuar_relevancia(texto: str, query: str) -> float:
    tokens_query = set(clean_query(query).split())
    tokens_texto = set(texto.lower().split())
    if not tokens_query or not tokens_texto:
        return 0.0
    return len(tokens_query & tokens_texto) / len(tokens_query)

def reclassificar_artigos_ia(artigos: List[Tuple[float, str, str]], query: str, use_gemini: bool, api_key: str, modelo: str) -> List[Tuple[float, str, str]]:
    """Usa IA para reclassificar os artigos por relevância"""
    if not artigos:
        return artigos
    
    try:
        artigos_info = []
        for score, url, conteudo in artigos:
            titulo = url.split('/')[-1].replace('-', ' ')[:100]
            if conteudo and len(conteudo) > 50:
                preview = conteudo[:200] + "..."
            else:
                preview = "Conteúdo não disponível"
            artigos_info.append(f"URL: {url}\nTítulo: {titulo}\nPreview: {preview}\n---")
        
        artigos_texto = "\n".join(artigos_info)
        
        if use_gemini:
            resposta = reclassificar_gemini(query, artigos_texto, modelo, api_key)
        else:
            resposta = reclassificar_openai(query, artigos_texto, modelo, api_key)
        
        artigos_ordenados = processar_resposta_reclassificacao(resposta, artigos)
        
        if artigos_ordenados:
            return artigos_ordenados
        else:
            return sorted(artigos, reverse=True, key=lambda x: x[0])
            
    except Exception as e:
        st.error(f"Erro na reclassificação por IA: {e}")
        return sorted(artigos, reverse=True, key=lambda x: x[0])

def reclassificar_gemini(query: str, artigos_texto: str, model: str, api_key: str) -> str:
    """Reclassifica artigos usando Gemini"""
    import google.generativeai as genai
    genai.configure(api_key=api_key)
    
    prompt = f"""
    Analise estes artigos da documentação TOTVS e ordene-os por relevância para a pergunta do usuário.
    
    PERGUNTA DO USUÁRIO: {query}
    
    ARTIGOS ENCONTRADOS:
    {artigos_texto}
    
    INSTRUÇÕES:
    1. Analise cada artigo em relação à pergunta
    2. Ordene do MAIS RELEVANTE para o MENOS RELEVANTE
    3. Retorne APENAS os URLs em ordem de relevância, um por linha
    4. Não inclua explicações, apenas a lista ordenada de URLs
    
    URLs ORDENADOS:
    """
    
    try:
        gemini_model = genai.GenerativeModel(model_name=model)
        response = gemini_model.generate_content([prompt])
        return response.text.strip()
    except Exception as e:
        raise Exception(f"Erro Gemini: {e}")

def reclassificar_openai(query: str, artigos_texto: str, model: str, api_key: str) -> str:
    """Reclassifica artigos usando OpenAI"""
    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    
    prompt = f"""
    Analise estes artigos da documentação TOTVS e ordene-os por relevância para a pergunta do usuário.
    
    PERGUNTA DO USUÁRIO: {query}
    
    ARTIGOS ENCONTRADOS:
    {artigos_texto}
    
    INSTRUÇÕES:
    1. Analise cada artigo em relação à pergunta
    2. Ordene do MAIS RELEVANTE para o MENOS RELEVANTE
    3. Retorne APENAS os URLs em ordem de relevância, um por linha
    4. Não inclua explicações, apenas a lista ordenada de URLs
    """
    
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Você é um especialista em classificar documentação técnica por relevância."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
            max_tokens=500,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        raise Exception(f"Erro OpenAI: {e}")

def processar_resposta_reclassificacao(resposta_ia: str, artigos_originais: List[Tuple[float, str, str]]) -> List[Tuple[float, str, str]]:
    """Processa a resposta da IA e reordena os artigos"""
    if not resposta_ia:
        return []
    
    urls_ordenados = []
    for linha in resposta_ia.split('\n'):
        linha = linha.strip()
        if linha.startswith('http'):
            urls_ordenados.append(linha)
    
    artigo_por_url = {url: (score, url, conteudo) for score, url, conteudo in artigos_originais}
    
    artigos_ordenados = []
    for url in urls_ordenados:
        if url in artigo_por_url:
            artigos_ordenados.append(artigo_por_url[url])
    
    urls_adicionados = set(urls_ordenados)
    for artigo in artigos_originais:
        if artigo[1] not in urls_adicionados:
            artigos_ordenados.append(artigo)
    
    return artigos_ordenados

# ---------------------------
# Formatação e Respostas
# ---------------------------
def formatar_links_saiba_mais(links: List[str]) -> str:
    """Formata os links para a seção Saiba Mais"""
    if not links:
        return ""
    
    padroes_de_remocao = ["-Cross", "-CROSS", "-RH", "-MP", "-Logística", "-Framework", "-LOG", "-FIN", "-FAT", "-CRM"]
    
    links_formatados = []
    for link in links:
        link_limpo = link
        for padrao in padroes_de_remocao:
            posicao = link.find(padrao)
            if posicao != -1:
                link_limpo = link[:posicao]
                break
        links_formatados.append(link_limpo)
    
    links_unicos = []
    for link in links_formatados:
        if link not in links_unicos:
            links_unicos.append(link)
    
    saiba_mais = "\n\n**🔗 Saiba mais:**\n"
    for i, link in enumerate(links_unicos[:5], 1):
        saiba_mais += f"{i}. {link}\n"
    
    return saiba_mais

def get_ai_response(query: str, context: str, fontes: List[str], modelo: str, use_gemini: bool, api_key: str, temperatura: float):
    """Função unificada que escolhe entre Gemini e ChatGPT"""
    
    if "erro 403" in context.lower() or "acesso negado" in context.lower():
        context = "Conteúdo não disponível devido a restrições de acesso."
    
    if not context or not context.strip() or context == "Conteúdo não disponível devido a restrições de acesso.":
        return "Não encontrei essa informação na documentação oficial devido a restrições de acesso."

    if use_gemini:
        return get_gemini_response(query, context, fontes, modelo, api_key, temperatura)
    else:
        return get_chatgpt_response(query, context, fontes, modelo, api_key, temperatura)

def get_gemini_response(query: str, context: str, fontes: List[str], model: str, api_key: str, temperatura: float):
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        
        generation_config = {
            "temperature": temperatura,
            "top_p": 0.0,
            "top_k": 40,
            "max_output_tokens": 1024,
        }
        
        gemini_model = genai.GenerativeModel(
            model_name=model,
            generation_config=generation_config
        )
        
        system_prompt = (
            "Você é um analista de suporte especializado no ERP Protheus da TOTVS.\n"
            "Responda de forma técnica, precisa e baseada exclusivamente no contexto fornecido.\n"
            "- Se a informação não estiver no contexto, responda apenas: \"Não encontrei essa informação na documentação oficial\".\n"
            "- Seja objetivo e inclua passos acionáveis quando aplicável.\n"
            "- NÃO inclua a seção 'Fontes consultadas' no final - isso será adicionado automaticamente.\n"
        )

        user_content = (
            f"{system_prompt}\n\n"
            f"PERGUNTA DO USUÁRIO:\n{query}\n\n"
            f"CONTEÚDO EXTRAÍDO:\n{context}\n\n"
            "Fontes disponíveis:\n" + "\n".join(fontes)
        )

        response = gemini_model.generate_content([user_content])
        return response.text.strip()
    except Exception as e:
        return f"Erro ao gerar resposta com Gemini: {e}"

def get_chatgpt_response(query: str, context: str, fontes: List[str], model: str, api_key: str, temperatura: float):
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        
        system_prompt = (
            "Você é um analista de suporte especializado no ERP Protheus da TOTVS.\n"
            "Responda de forma técnica, precisa e baseada exclusivamente no contexto fornecido.\n"
            "- Se a informação não estiver no contexto, responda apenas: \"Não encontrei essa informação na documentação oficial\".\n"
            "- Seja objetivo e inclua passos acionáveis quando aplicável.\n"
            "- NÃO inclua a seção 'Fontes consultadas' no final - isso será adicionado automaticamente.\n"
        )
        
        user_content = f"PERGUNTA DO USUÁRIO:\n{query}\n\nCONTEÚDO EXTRAÍDO:\n{context}\n\nFontes disponíveis:\n" + "\n".join(fontes)

        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            temperature=temperatura,
            max_tokens=512,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"Erro ao gerar resposta com OpenAI: {e}"

# ---------------------------
# Verificação de Status do Site
# ---------------------------
def verificar_status_site():
    """Verifica o status do site e possíveis bloqueios"""
    test_url = "https://centraldeatendimento.totvs.com/hc/pt-br"
    
    try:
        response = requests.get(test_url, headers=get_totvs_specific_headers(), timeout=10)
        
        if response.status_code == 200:
            st.success("✅ Site da TOTVS está acessível")
            return True
        elif response.status_code == 403:
            st.error("❌ Site está bloqueando acesso automático")
            st.info("💡 **Soluções possíveis:**")
            st.info("- Aguarde alguns minutos e tente novamente")
            st.info("- O site pode estar com rate limiting ativo")
            st.info("- Use a opção Selenium para contornar bloqueios")
            return False
        else:
            st.warning(f"⚠️ Site retornou status {response.status_code}")
            return False
            
    except Exception as e:
        st.error(f"🔌 Erro de conexão: {e}")
        return False

# ---------------------------
# Processamento Principal
# ---------------------------
def processar_pergunta(user_query: str):
    """Processa a pergunta do usuário e retorna a resposta"""
    
    if not st.session_state.api_key:
        return "Erro: Chave da API não configurada. Por favor, configure sua chave na sidebar."
    
    # Verificar status do site
    with st.status("Verificando acesso ao site...") as status:
        status.write("🔍 Testando conexão com a TOTVS...")
        if not verificar_status_site():
            return "❌ **Problema de acesso detectado:** O site da TOTVS está bloqueando nosso acesso no momento. Tente:\n\n1. Ativar a opção 'Usar Selenium' na sidebar\n2. Aguardar alguns minutos\n3. Tentar novamente mais tarde"
    
    cleaned_query = clean_query(user_query)
    if not cleaned_query:
        return "Não foi possível processar a pergunta."

    if tem_video_ou_anexo(user_query):
        return "Pergunta contém referência a vídeo ou anexo. Não será feita busca automática na documentação."
    
    try:
        # Buscar links
        with st.status("Buscando na documentação TOTVS...", expanded=True) as status:
            status.write("🔍 Procurando artigos relevantes...")
            links = buscar_documentacao_totvs(user_query, max_links=5)
            
            if not links:
                return "Não foram encontrados artigos relevantes na documentação TOTVS."
            
            status.write(f"📚 Encontrados {len(links)} artigos. Extraindo conteúdo...")
            contexto_scores = []
            
            # Extrair conteúdo dos links
            for i, link in enumerate(links):
                status.write(f"📖 Lendo artigo {i+1}/{len(links)}...")
                texto = extrair_conteudo_pagina(link)
                score = pontuar_relevancia(texto, user_query)
                contexto_scores.append((score, link, texto))

            # Reclassificação inteligente por IA
            if st.session_state.reclassificar_ia and len(contexto_scores) > 1:
                status.write("🧠 Reclassificando artigos por relevância...")
                contexto_scores = reclassificar_artigos_ia(
                    contexto_scores, 
                    user_query, 
                    st.session_state.use_gemini,
                    st.session_state.api_key,
                    st.session_state.modelo
                )
            else:
                contexto_scores.sort(reverse=True, key=lambda x: x[0])
            
            status.write("🤖 Gerando resposta com IA...")
            
            artigos_relevantes = contexto_scores[:3]
            contexto_combinado = "\n\n".join([conteudo for _, _, conteudo in artigos_relevantes if conteudo.strip()])
            
            if not contexto_combinado.strip():
                resposta_final = "Atenção: não foi possível validar essa informação específica na documentação oficial."
            elif contexto_scores[0][0] < st.session_state.min_score:
                resposta_final = "Observação: essa consulta aborda um ponto não detalhado na documentação. A resposta é baseada em conhecimento geral.\n\n"
                resposta_final += get_ai_response(
                    user_query, 
                    contexto_combinado, 
                    [link for _, link, _ in artigos_relevantes], 
                    st.session_state.modelo,
                    st.session_state.use_gemini,
                    st.session_state.api_key,
                    st.session_state.temperatura
                )
            else:
                resposta_final = get_ai_response(
                    user_query, 
                    contexto_combinado, 
                    [link for _, link, _ in artigos_relevantes], 
                    st.session_state.modelo,
                    st.session_state.use_gemini,
                    st.session_state.api_key,
                    st.session_state.temperatura
                )
            
            mensagens_erro = [
                "não foi possível validar essa informação específica",
                "não encontrei essa informação na documentação oficial",
                "conteúdo não disponível devido a restrições de acesso"
            ]
            
            resposta_valida = not any(erro in resposta_final.lower() for erro in mensagens_erro)
            
            if resposta_valida and links:
                saiba_mais = formatar_links_saiba_mais([link for _, link, _ in contexto_scores[:5]])
                resposta_final += saiba_mais
            
            status.update(label="Processamento completo!", state="complete")
            
        return resposta_final

    except Exception as e:
        return f"Ocorreu um erro durante o processamento: {str(e)}"

# ---------------------------
# Interface Streamlit
# ---------------------------
def inicializar_session_state():
    """Inicializa as variáveis de session state"""
    if 'min_score' not in st.session_state:
        st.session_state.min_score = 0.5
    if 'use_gemini' not in st.session_state:
        st.session_state.use_gemini = True
    if 'modelo' not in st.session_state:
        st.session_state.modelo = "gemini-1.5-flash"
    if 'api_key' not in st.session_state:
        st.session_state.api_key = ""
    if 'temperatura' not in st.session_state:
        st.session_state.temperatura = 0.0
    if 'mostrar_codigo' not in st.session_state:
        st.session_state.mostrar_codigo = False
    if 'reclassificar_ia' not in st.session_state:
        st.session_state.reclassificar_ia = True
    if 'usar_selenium' not in st.session_state:
        st.session_state.usar_selenium = True

def atualizar_lista_modelos():
    """Atualiza a lista de modelos baseado na escolha Gemini/OpenAI"""
    if st.session_state.use_gemini:
        modelos_disponiveis = ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-pro"]
        if not st.session_state.modelo.startswith("gemini"):
            st.session_state.modelo = "gemini-1.5-flash"
    else:
        modelos_disponiveis = ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo", "gpt-4", "gpt-4-turbo"]
        if not any(model in st.session_state.modelo for model in ["gpt", "openai"]):
            st.session_state.modelo = "gpt-4o-mini"
    return modelos_disponiveis

def main():
    # Inicializar session state
    inicializar_session_state()
    
    # Sidebar para configurações
    with st.sidebar:
        st.header("⚙️ Configurações")
        
        # Configurações de IA
        st.session_state.use_gemini = st.checkbox(
            "Usar Google Gemini",
            value=st.session_state.use_gemini,
            help="Desmarque para usar OpenAI"
        )
        
        modelos_disponiveis = atualizar_lista_modelos()
        
        # Configurações de Acesso
        st.subheader("🛡️ Configurações de Acesso")
        
        if SELENIUM_AVAILABLE:
            st.session_state.usar_selenium = st.checkbox(
                "🤖 Usar Selenium (Recomendado)",
                value=st.session_state.usar_selenium,
                help="Usa navegador real para evitar bloqueios - mais lento mas mais eficaz"
            )
        else:
            st.warning("Selenium não disponível. Instale: pip install selenium webdriver-manager")
            st.session_state.usar_selenium = False
        
        st.session_state.reclassificar_ia = st.checkbox(
            "🧠 Reclassificação Inteligente por IA",
            value=st.session_state.reclassificar_ia,
            help="Usa IA para reordenar artigos por relevância"
        )
        
        # Configurações de Performance
        st.subheader("🎯 Configurações de Performance")
        
        st.session_state.min_score = st.slider(
            "Score Mínimo de Relevância",
            min_value=0.0,
            max_value=1.0,
            value=st.session_state.min_score,
            step=0.1,
            help="Quanto maior o score, mais relevante precisa ser o conteúdo"
        )
        
        st.session_state.temperatura = st.slider(
            "🌡️ Temperatura da IA",
            min_value=0.0,
            max_value=1.0,
            value=st.session_state.temperatura,
            step=0.1,
            help="Valores mais baixos = respostas mais focadas e determinísticas"
        )
        
        # Modelo e API
        st.session_state.modelo = st.selectbox(
            "🤖 Modelo de IA",
            options=modelos_disponiveis,
            index=modelos_disponiveis.index(st.session_state.modelo) if st.session_state.modelo in modelos_disponiveis else 0
        )
        
        st.session_state.api_key = st.text_input(
            "🔑 Chave da API",
            value=st.session_state.api_key,
            type="password",
            placeholder="Cole sua chave da API aqui",
            help="Obtenha sua chave em: https://aistudio.google.com/ (Gemini) ou https://platform.openai.com/ (OpenAI)"
        )
        
        # Indicador visual da temperatura
        col_temp1, col_temp2, col_temp3 = st.columns(3)
        with col_temp1:
            if st.session_state.temperatura <= 0.3:
                st.metric("Estilo", "Preciso", delta="Focado")
        with col_temp2:
            if 0.4 <= st.session_state.temperatura <= 0.7:
                st.metric("Estilo", "Balanceado", delta="Equilibrado")
        with col_temp3:
            if st.session_state.temperatura >= 0.8:
                st.metric("Estilo", "Criativo", delta="Variado")
        
        st.markdown("---")
        st.info("""
        **💡 Dicas:**
        - Ative 'Usar Selenium' para evitar bloqueios 403
        - Configure sua chave de API para usar o assistente
        - Score 0.3-0.5 para maior precisão
        - Temperatura 0.1-0.3 para suporte técnico
        """)
        
        # Status do Selenium
        if SELENIUM_AVAILABLE:
            st.success("✅ Selenium disponível")
        else:
            st.error("❌ Selenium não disponível")
        
        st.markdown("---")
        st.caption("By Evandro Narciso Santos")
    
    # Conteúdo principal
    st.title("🤖 Responde AI TOTVS")
    st.markdown("Sua assistente inteligente para dúvidas sobre o **ERP Protheus**")
    
    # Indicador de configuração
    ai_provider = "Google Gemini" if st.session_state.use_gemini else "OpenAI"
    temp_desc = "Preciso" if st.session_state.temperatura <= 0.3 else "Balanceado" if st.session_state.temperatura <= 0.7 else "Criativo"
    reclass_desc = "✅ Ativa" if st.session_state.reclassificar_ia else "❌ Inativa"
    selenium_desc = "✅ Ativo" if st.session_state.usar_selenium and SELENIUM_AVAILABLE else "❌ Inativo"
    
    st.caption(f"🔧 Configurado: {ai_provider} | Modelo: {st.session_state.modelo} | Score: {st.session_state.min_score} | Temperatura: {st.session_state.temperatura} ({temp_desc}) | Reclassificação IA: {reclass_desc} | Selenium: {selenium_desc}")
    
    # Área de entrada da pergunta
    user_query = st.text_area(
        "**Digite sua pergunta:**",
        placeholder="Ex: Como configurar parâmetros financeiros no Protheus?",
        height=150,
        help="Descreva sua dúvida técnica sobre o ERP Protheus"
    )
    
    # Botão de envio
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("🚀 Enviar Pergunta", type="primary", use_container_width=True):
            if not user_query.strip():
                st.warning("Por favor, digite sua pergunta.")
            else:
                if not st.session_state.api_key:
                    st.error("❌ Configure sua chave da API na sidebar para continuar.")
                else:
                    resposta = processar_pergunta(user_query)
                    st.session_state.resposta = resposta
                    st.session_state.mostrar_codigo = False
    
    with col2:
        if st.button("🧹 Limpar", use_container_width=True):
            if 'resposta' in st.session_state:
                del st.session_state.resposta
            st.session_state.mostrar_codigo = False
            st.rerun()
    
    # Exibir resposta se existir
    if 'resposta' in st.session_state and st.session_state.resposta:
        st.markdown("---")
        st.subheader("📋 Resposta:")
        
        # Controles para a resposta
        col_controls1, col_controls2, col_controls3 = st.columns([2, 1, 1])
        
        with col_controls1:
            if st.button("📄 Visualizar como Código" if not st.session_state.mostrar_codigo else "📝 Visualizar Normal", 
                        key="toggle_view", use_container_width=True):
                st.session_state.mostrar_codigo = not st.session_state.mostrar_codigo
                st.rerun()
        
        with col_controls2:
            if st.button("📋 Copiar Resposta", key="copy_btn", use_container_width=True):
                st.session_state.mostrar_codigo = True
                st.success("✅ Use Ctrl+C para copiar o texto acima!")
        
        with col_controls3:
            if st.button("💾 Baixar", key="download_btn", use_container_width=True):
                st.download_button(
                    label="📥 Clique para baixar",
                    data=st.session_state.resposta,
                    file_name=f"resposta_totvs_{time.strftime('%Y%m%d_%H%M%S')}.txt",
                    mime="text/plain",
                    key="download_file"
                )
        
        # Exibir a resposta
        if st.session_state.mostrar_codigo:
            st.code(st.session_state.resposta, language="text", line_numbers=False)
            st.info("💡 **Dica:** Selecione o texto acima e use Ctrl+C para copiar")
        else:
            st.write(st.session_state.resposta)

if __name__ == "__main__":
    main()
