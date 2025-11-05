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
import json

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
# HEADERS REAIS CAPTURADOS DO NAVEGADOR
# ---------------------------
def get_real_headers():
    """Headers reais capturados do navegador que funcionam"""
    return {
        'authority': 'centraldeatendimento.totvs.com',
        'method': 'GET',
        'scheme': 'https',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'accept-encoding': 'gzip, deflate, br, zstd',
        'accept-language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
        'cache-control': 'max-age=0',
        'cookie': '_gid=GA1.2.389367704.1762177997; _ga_8RWQ11H2P1=GS2.1.s1762177996$o1$g1$t1762179312$j60$l0$h0; __cf_bm=77.I6AAf1XGwaZCc8CyuePaCSC2QQ41lmV1EdgqGXDQ-1762199821-1.0.1.1-lEtOUyWSjfNVl6PgK0cedKcWQtZq0NOd4dfG0224QqJxjxTRRwRqmKVaNS66Pkfx.Yd7i8pVyHbYFyqpQVSom_.XSi8O6bU4E1ETM3cxt0U; _cfuvid=mKxrTNR60oHIIZbpnSJy12OPdjXI_FfMYWG8JAohJm0-1762199821243-0.0.1.1-604800000; _ga=GA1.2.66637372.1762177997; __insp_wid=96774380; __insp_nv=true; __insp_targlpu=aHR0cHM6Ly9jZW50cmFsZGVhdGVuZGltZW50by50b3R2cy5jb20vaGMvcHQtYnIvc2VjdGlvbnMvMTE1MDA0MDg5Nzg3LVRlbXBsYXRlLUtDUz9wYWdlPTEjYXJ0aWNsZXM%3D; __insp_targlpt=VGVtcGxhdGUgS0NTIOKAkyBDZW50cmFsIGRlIEF0ZW5kaW1lbnRvIFRPVFZT; __insp_norec_sess=true; _zendesk_cookie=BAhJIhl7ImRldmljZV90b2tlbnMiOnt9fQY6BkVU--0bf2100788cb010d0183feca16aaf88ccaf719ca; __zlcmid=1URo2Rzyxc6uLns; __insp_slim=1762200030667; _ga_7H9MK30MKR=GS2.2.s1762199822$o1$g1$t1762200030$j60$l0$h0; _help_center_session=ZTJ6TG82cU1UdEFvZHlkSHl1dmkyUUp2Qktnd0YyTmlUSi8zRlhON2h1Mlh3RjB5QzhiUnkwWjVYVi9MdkdaMVM0cUVRRFpMYTgxcHVMQXVWK3M2Um5Ub2ZhTEdRM0pqVDdVSkM0UzJON1c3SWlsTExkN0ZWb3BzK01NdUNNTWZDVjkrYjVsYXlxVXh3V2tKeUpFVC9rNWVMb1NCSUFQRjlFeXlIUFp3RzFmYTd4ZUxYZlV4aW9BTTYzdFZhQVlULS0wSXltTmdYV1Z0YlFNSmwrb2R6M0V3PT0%3D--a86ab5913fe6c42c14f18f3ced61b56b1791726f',
        'priority': 'u=0, i',
        'sec-ch-ua': '"Google Chrome";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'cross-site',
        'sec-fetch-user': '?1',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36'
    }

def get_headers_for_url(url):
    """Retorna headers específicos para cada URL"""
    headers = get_real_headers()
    headers[':path'] = urllib.parse.urlparse(url).path
    headers['referer'] = 'https://centraldeatendimento.totvs.com/'
    return headers

# ---------------------------
# SESSÃO PERSONALIZADA COM HEADERS REAIS
# ---------------------------
def create_authenticated_session():
    """Cria uma sessão com cookies e headers reais"""
    session = requests.Session()
    
    # Atualizar headers padrão da sessão
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br',
        'Upgrade-Insecure-Requests': '1',
    })
    
    return session

# Criar sessão autenticada
session = create_authenticated_session()

# ---------------------------
# SISTEMA DE BUSCA DIRETA
# ---------------------------
def fazer_requisicao_direta(url):
    """Faz requisição direta com headers reais"""
    try:
        headers = get_headers_for_url(url)
        response = session.get(url, headers=headers, timeout=30)
        return response
    except Exception as e:
        st.error(f"Erro na requisição: {e}")
        return None

def extrair_conteudo_direto(url):
    """Extrai conteúdo diretamente com headers reais"""
    try:
        response = fazer_requisicao_direta(url)
        
        if response and response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remover elementos desnecessários
            for element in soup(['script', 'style', 'nav', 'footer', 'header']):
                element.decompose()
            
            # Buscar conteúdo principal
            content = None
            selectors = [
                'article',
                '.article-body',
                '.article-content',
                'main',
                '.main-content'
            ]
            
            for selector in selectors:
                content = soup.select_one(selector)
                if content:
                    break
            
            if content:
                text = content.get_text(separator=' ', strip=True)
            else:
                text = soup.get_text(separator=' ', strip=True)
            
            return clean_text(text)[:6000]
        else:
            return f"Erro: Status {response.status_code if response else 'No response'}"
            
    except Exception as e:
        return f"Erro na extração: {str(e)}"

# ---------------------------
# BUSCA VIA DUCKDUCKGO (Fallback)
# ---------------------------
def buscar_links_ddg(query, max_results=5):
    """Busca links via DuckDuckGo"""
    try:
        search_query = f"site:centraldeatendimento.totvs.com {query}"
        links = []
        
        with DDGS() as ddgs:
            for result in ddgs.text(search_query, max_results=max_results):
                url = result.get('href', '')
                if 'centraldeatendimento.totvs.com' in url and '/articles/' in url:
                    links.append(url)
        
        return links
    except Exception as e:
        st.error(f"Erro no DuckDuckGo: {e}")
        return []

# ---------------------------
# FUNÇÕES DE PROCESSAMENTO
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

# ---------------------------
# SISTEMA PRINCIPAL DE BUSCA
# ---------------------------
def buscar_documentacao_totvs(query: str, max_links: int = 5) -> List[str]:
    """Busca documentos TOTVS usando métodos combinados"""
    cleaned = clean_query(query)
    
    st.info("🔍 Buscando na documentação TOTVS...")
    
    # Buscar via DuckDuckGo
    links = buscar_links_ddg(cleaned, max_links)
    
    if links:
        st.success(f"✅ Encontrados {len(links)} artigos")
        return links
    else:
        st.warning("⚠️ Não foram encontrados artigos específicos")
        # Retornar link de pesquisa como fallback
        return [f"https://centraldeatendimento.totvs.com/hc/pt-br/search?query={urllib.parse.quote(cleaned)}"]

def extrair_conteudo_pagina(url: str) -> str:
    """Extrai conteúdo da página usando headers reais"""
    if '/search?' in url:
        return "Página de pesquisa - use os links de artigos específicos"
    
    return extrair_conteudo_direto(url)

# ---------------------------
# SISTEMA IA (mantido igual)
# ---------------------------
def pontuar_relevancia(texto: str, query: str) -> float:
    tokens_query = set(clean_query(query).split())
    tokens_texto = set(texto.lower().split())
    if not tokens_query or not tokens_texto:
        return 0.0
    return len(tokens_query & tokens_texto) / len(tokens_query)

def get_ai_response(query: str, context: str, fontes: List[str], modelo: str, use_gemini: bool, api_key: str, temperatura: float):
    if "erro" in context.lower() or "não acessível" in context.lower():
        return "Não foi possível acessar a documentação oficial para esta consulta."

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
        
        prompt = f"""
        Você é um especialista em ERP Protheus da TOTVS.
        Baseie sua resposta exclusivamente no contexto fornecido.
        
        PERGUNTA: {query}
        
        CONTEXTO:
        {context}
        
        Responda de forma técnica e precisa. Se a informação não estiver no contexto, diga apenas "Não encontrei essa informação na documentação".
        """
        
        response = gemini_model.generate_content([prompt])
        return response.text.strip()
    except Exception as e:
        return f"Erro Gemini: {e}"

def get_chatgpt_response(query: str, context: str, fontes: List[str], model: str, api_key: str, temperatura: float):
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        
        prompt = f"""
        Você é um especialista em ERP Protheus da TOTVS.
        Baseie sua resposta exclusivamente no contexto fornecido.
        
        PERGUNTA: {query}
        
        CONTEXTO:
        {context}
        
        Responda de forma técnica e precisa. Se a informação não estiver no contexto, diga apenas "Não encontrei essa informação na documentação".
        """
        
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Você é um analista de suporte especializado no ERP Protheus."},
                {"role": "user", "content": prompt},
            ],
            temperature=temperatura,
            max_tokens=512,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"Erro OpenAI: {e}"

# ---------------------------
# PROCESSAMENTO PRINCIPAL
# ---------------------------
def processar_pergunta(user_query: str):
    if not st.session_state.api_key:
        return "Erro: Configure sua chave da API na sidebar."
    
    cleaned_query = clean_query(user_query)
    if not cleaned_query:
        return "Não foi possível processar a pergunta."
    
    try:
        with st.status("Processando sua pergunta...", expanded=True) as status:
            status.write("🔍 Buscando artigos relevantes...")
            links = buscar_documentacao_totvs(user_query, max_links=3)
            
            if not links or (len(links) == 1 and 'search?' in links[0]):
                return "Não foram encontrados artigos específicos para sua consulta."
            
            status.write(f"📚 Analisando {len(links)} artigos...")
            artigos_com_conteudo = []
            
            for i, link in enumerate(links):
                status.write(f"📖 Lendo artigo {i+1}...")
                conteudo = extrair_conteudo_pagina(link)
                score = pontuar_relevancia(conteudo, user_query)
                artigos_com_conteudo.append((score, link, conteudo))
            
            # Ordenar por relevância
            artigos_com_conteudo.sort(reverse=True, key=lambda x: x[0])
            
            status.write("🤖 Gerando resposta...")
            
            # Usar os 2 artigos mais relevantes
            artigos_relevantes = artigos_com_conteudo[:2]
            contexto = "\n\n".join([conteudo for _, _, conteudo in artigos_relevantes])
            
            resposta = get_ai_response(
                user_query, 
                contexto, 
                [link for _, link, _ in artigos_relevantes], 
                st.session_state.modelo,
                st.session_state.use_gemini,
                st.session_state.api_key,
                st.session_state.temperatura
            )
            
            # Adicionar links de referência
            if "não encontrei" not in resposta.lower():
                resposta += "\n\n**🔗 Referências:**\n"
                for i, (_, link, _) in enumerate(artigos_relevantes, 1):
                    resposta += f"{i}. {link}\n"
            
            status.update(label="✅ Processamento completo!", state="complete")
            return resposta
            
    except Exception as e:
        return f"Erro no processamento: {str(e)}"

# ---------------------------
# INTERFACE STREAMLIT
# ---------------------------
def inicializar_session_state():
    if 'min_score' not in st.session_state:
        st.session_state.min_score = 0.3
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

def main():
    inicializar_session_state()
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configurações")
        
        st.session_state.use_gemini = st.checkbox(
            "Usar Google Gemini", value=st.session_state.use_gemini
        )
        
        modelos = ["gemini-1.5-flash", "gemini-1.5-pro"] if st.session_state.use_gemini else ["gpt-4o-mini", "gpt-4o"]
        st.session_state.modelo = st.selectbox("Modelo", modelos)
        
        st.session_state.api_key = st.text_input(
            "Chave da API", 
            value=st.session_state.api_key, 
            type="password"
        )
        
        st.session_state.temperatura = st.slider(
            "Temperatura", 0.0, 1.0, st.session_state.temperatura
        )
        
        st.info("""
        **💡 Dica:** 
        Este sistema usa headers reais do navegador para acessar a documentação TOTVS.
        """)
    
    # Main
    st.title("🤖 Responde AI TOTVS")
    st.markdown("Assistente para dúvidas sobre **ERP Protheus**")
    
    user_query = st.text_area(
        "Digite sua pergunta:",
        placeholder="Ex: Como configurar parâmetros fiscais no Protheus?",
        height=100
    )
    
    if st.button("🚀 Enviar Pergunta", type="primary"):
        if user_query.strip():
            if st.session_state.api_key:
                resposta = processar_pergunta(user_query)
                st.session_state.resposta = resposta
            else:
                st.error("❌ Configure sua chave da API")
        else:
            st.warning("⚠️ Digite uma pergunta")
    
    if 'resposta' in st.session_state:
        st.markdown("---")
        st.subheader("📋 Resposta:")
        st.write(st.session_state.resposta)

if __name__ == "__main__":
    main()
