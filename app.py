import streamlit as st
import os
import re
import urllib.parse
from typing import List, Set
import pandas as pd
import requests
from bs4 import BeautifulSoup
from ddgs import DDGS
import cloudscraper
import pyperclip  # Adicione esta importação

# ---------------------------
# Configuração Inicial
# ---------------------------
st.set_page_config(
    page_title="Responde AI TOTVS",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inicializar scraper
scraper = cloudscraper.create_scraper()

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

def pesquisar_interna_totvs(query: str, limit: int = 8) -> List[str]:
    base = "https://centraldeatendimento.totvs.com"
    search_url = f"{base}/hc/pt-br/search?query={urllib.parse.quote(query)}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'pt-BR,pt;q=0.9',
        'Referer': 'https://centraldeatendimento.totvs.com/',
    }

    links = []
    try:
        resp = scraper.get(search_url, headers=headers, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, "html.parser")
        for a in soup.select("a[href*='/articles/']"):
            href = a.get("href")
            if not href:
                continue
            if href.startswith("/"):
                href = base + href
            if href.startswith(base) and href not in links:
                links.append(href)
            if len(links) >= limit:
                break
    except Exception as e:
        st.error(f"Erro na pesquisa interna: {e}")
    return links

def buscar_documentacao_totvs(query: str, max_links: int = 5) -> List[str]:
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

def extrair_conteudo_pagina(url: str) -> str:
    if '/search?' in url:
        return "Página de pesquisa - conteúdo não extraído"

    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        resp = scraper.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, 'html.parser')
        for el in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', 'form']):
            el.decompose()
        content = soup.select_one("article") or soup.select_one("main") or soup.select_one(".article-body")
        if content:
            for el in content.select('.article-attachments, .article-meta, .article-votes'):
                el.decompose()
            text = content.get_text(separator=' ', strip=True)
        else:
            text = soup.get_text(separator=' ', strip=True)
        return clean_text(text)[:6000]
    except Exception as e:
        st.error(f"Erro ao extrair conteúdo: {e}")
        return ""

def pontuar_relevancia(texto: str, query: str) -> float:
    tokens_query = set(clean_query(query).split())
    tokens_texto = set(texto.lower().split())
    if not tokens_query or not tokens_texto:
        return 0.0
    return len(tokens_query & tokens_texto) / len(tokens_query)

def get_ai_response(query: str, context: str, fontes: List[str], modelo: str, use_gemini: bool, api_key: str):
    """Função unificada que escolhe entre Gemini e ChatGPT"""
    
    if not context or not context.strip():
        return "Não encontrei essa informação na documentação oficial"

    if use_gemini:
        return get_gemini_response(query, context, fontes, modelo, api_key)
    else:
        return get_chatgpt_response(query, context, fontes, modelo, api_key)

def get_gemini_response(query: str, context: str, fontes: List[str], model: str, api_key: str):
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        gemini_model = genai.GenerativeModel(model_name=model)
        
        system_prompt = (
            "Você é um analista de suporte especializado no ERP Protheus da TOTVS.\n"
            "Responda de forma técnica, precisa e baseada exclusivamente no contexto fornecido.\n"
            "- Se a informação não estiver no contexto, responda apenas: \"Não encontrei essa informação na documentação oficial\".\n"
            "- Seja objetivo e inclua passos acionáveis quando aplicável.\n"
            "- Ao final, adicione a seção 'Fontes consultadas' com os links.\n"
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

def get_chatgpt_response(query: str, context: str, fontes: List[str], model: str, api_key: str):
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        
        system_prompt = (
            "Você é um analista de suporte especializado no ERP Protheus da TOTVS.\n"
            "Responda de forma técnica, precisa e baseada exclusivamente no contexto fornecido.\n"
            "- Se a informação não estiver no contexto, responda apenas: \"Não encontrei essa informação na documentação oficial\".\n"
            "- Seja objetivo e inclua passos acionáveis quando aplicável.\n"
            "- Ao final, adicione a seção 'Fontes consultadas' com os links.\n"
        )
        
        user_content = f"PERGUNTA DO USUÁRIO:\n{query}\n\nCONTEÚDO EXTRAÍDO:\n{context}\n\nFontes disponíveis:\n" + "\n".join(fontes)

        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            temperature=0.0,
            max_tokens=512,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"Erro ao gerar resposta com OpenAI: {e}"

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
        st.session_state.modelo = "gemini-2.0-flash"
    if 'api_key' not in st.session_state:
        st.session_state.api_key = ""

def atualizar_lista_modelos():
    """Atualiza a lista de modelos baseado na escolha Gemini/OpenAI"""
    if st.session_state.use_gemini:
        modelos_disponiveis = ["gemini-2.5-pro","gemini-2.5-flash","gemini-2.0-pro","gemini-2.0-flash","gemini-1.5-pro"]
        if not st.session_state.modelo.startswith("gemini"):
            st.session_state.modelo = "gemini-2.0-flash"
    else:
        modelos_disponiveis = ["gpt-5","gpt-5-mini","gpt-5-nano","gpt-4.1","gpt-4.1-mini","gpt-4.1-nano","gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo", "gpt-4", "gpt-4-turbo"]
        if not any(model in st.session_state.modelo for model in ["gpt", "openai"]):
            st.session_state.modelo = "gpt-4o-mini"
    return modelos_disponiveis

def copiar_para_area_transferencia(texto: str):
    """Copia texto para área de transferência"""
    try:
        pyperclip.copy(texto)
        return True
    except Exception as e:
        st.error(f"Erro ao copiar: {e}")
        return False

def processar_pergunta(user_query: str):
    """Processa a pergunta do usuário e retorna a resposta"""
    # Verificar se a API key foi configurada
    if not st.session_state.api_key:
        return "Erro: Chave da API não configurada. Por favor, configure sua chave na sidebar."
    
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
            for i, link in enumerate(links[:3]):
                status.write(f"📖 Lendo artigo {i+1}/3...")
                texto = extrair_conteudo_pagina(link)
                score = pontuar_relevancia(texto, user_query)
                contexto_scores.append((score, link, texto))

            contexto_scores.sort(reverse=True, key=lambda x: x[0])
            
            status.write("🤖 Gerando resposta com IA...")
            
            # Gerar resposta
            if not contexto_scores or not contexto_scores[0][2].strip():
                resposta_final = "Atenção: não foi possível validar essa informação específica na documentação oficial."
            elif contexto_scores[0][0] < st.session_state.min_score:
                resposta_final = "Observação: essa consulta aborda um ponto não detalhado na documentação. A resposta é baseada em conhecimento geral.\n\n"
                resposta_final += get_ai_response(
                    user_query, 
                    contexto_scores[0][2], 
                    links, 
                    st.session_state.modelo,
                    st.session_state.use_gemini,
                    st.session_state.api_key
                )
            else:
                resposta_final = get_ai_response(
                    user_query, 
                    contexto_scores[0][2], 
                    links, 
                    st.session_state.modelo,
                    st.session_state.use_gemini,
                    st.session_state.api_key
                )
            
            status.update(label="Processamento completo!", state="complete")
            
        return resposta_final

    except Exception as e:
        return f"Ocorreu um erro durante o processamento: {str(e)}"

def main():
    # Inicializar session state
    inicializar_session_state()
    
    # Sidebar para configurações
    with st.sidebar:
        st.header("⚙️ Configurações")
        
        # Checkbox para escolher entre Gemini e OpenAI
        st.session_state.use_gemini = st.checkbox(
            "Usar Google Gemini",
            value=st.session_state.use_gemini,
            help="Desmarque para usar OpenAI"
        )
        
        # Lista de modelos atualizada
        modelos_disponiveis = atualizar_lista_modelos()
        
        # Configurações
        st.session_state.min_score = st.slider(
            "Score Mínimo de Relevância",
            min_value=0.0,
            max_value=1.0,
            value=st.session_state.min_score,
            step=0.1,
            help="Quanto maior o score, mais relevante precisa ser o conteúdo"
        )
        
        st.session_state.modelo = st.selectbox(
            "Modelo de IA",
            options=modelos_disponiveis,
            index=modelos_disponiveis.index(st.session_state.modelo) if st.session_state.modelo in modelos_disponiveis else 0
        )
        
        st.session_state.api_key = st.text_input(
            "Chave da API",
            value=st.session_state.api_key,
            type="password",
            placeholder="Cole sua chave da API aqui",
            help="Obtenha sua chave em: https://aistudio.google.com/ (Gemini) ou https://platform.openai.com/ (OpenAI)"
        )
        
        st.markdown("---")
        st.info("""
        **💡 Dicas:**
        - Faça perguntas específicas sobre o ERP Protheus
        - Use termos técnicos para melhores resultados
        - Configure sua chave de API para usar o assistente
        """)
        
        st.markdown("---")
        st.caption("By Evandro Narciso Santos")
    
    # Conteúdo principal
    st.title("🤖 Assistente de Suporte TOTVS")
    st.markdown("Sua assistente inteligente para dúvidas sobre o **ERP Protheus**")
    
    # Indicador de configuração
    ai_provider = "Google Gemini" if st.session_state.use_gemini else "OpenAI"
    st.caption(f"🔧 Configurado: {ai_provider} | Modelo: {st.session_state.modelo} | Score: {st.session_state.min_score}")
    
    # Área de entrada da pergunta
    user_query = st.text_area(
        "**Digite sua pergunta:**",
        placeholder="Ex: Como configurar parâmetros financeiros no Protheus?",
        height=120,
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
    
    with col2:
        if st.button("🧹 Limpar", use_container_width=True):
            if 'resposta' in st.session_state:
                del st.session_state.resposta
            st.rerun()
    
    # Exibir resposta se existir
    if 'resposta' in st.session_state and st.session_state.resposta:
        st.markdown("---")
        st.subheader("📋 Resposta:")
        
        # Área da resposta com botão de copiar
        col_resp1, col_resp2 = st.columns([4, 1])
        
        with col_resp1:
            st.write(st.session_state.resposta)
        
        with col_resp2:
            if st.button("📋 Copiar", key="copiar_btn", use_container_width=True):
                if copiar_para_area_transferencia(st.session_state.resposta):
                    st.success("✅ Copiado!")
                else:
                    st.error("❌ Erro ao copiar")
            
            # Botão para visualizar como código
            if st.button("📄 Código", key="codigo_btn", use_container_width=True):
                st.code(st.session_state.resposta, language="text")

if __name__ == "__main__":
    main()
