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
from datetime import datetime

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
# SISTEMA DE CACHE PARA MELHOR PERFORMANCE
# ---------------------------
class CacheManager:
    def __init__(self, ttl=3600):  # 1 hora de cache
        self.cache = {}
        self.ttl = ttl
    
    def get(self, key):
        if key in self.cache:
            data, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl:
                return data
            else:
                del self.cache[key]
        return None
    
    def set(self, key, value):
        self.cache[key] = (value, time.time())
    
    def clear(self):
        self.cache.clear()

cache = CacheManager()

# ---------------------------
# HEADERS MELHORADOS COM ROTAÇÃO DINÂMICA
# ---------------------------
def get_dynamic_headers(url=None):
    """Retorna headers dinâmicos e realistas"""
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36'
    ]
    
    base_headers = {
        'authority': 'centraldeatendimento.totvs.com',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'accept-language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
        'cache-control': 'no-cache',
        'pragma': 'no-cache',
        'sec-ch-ua': '"Google Chrome";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'same-origin',
        'upgrade-insecure-requests': '1',
        'user-agent': random.choice(user_agents),
    }
    
    if url:
        base_headers['referer'] = 'https://centraldeatendimento.totvs.com/'
    
    return base_headers

# ---------------------------
# SISTEMA DE REQUISIÇÕES ROBUSTO
# ---------------------------
def create_advanced_scraper():
    """Cria um scraper avançado com retry automático"""
    try:
        scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'mobile': False
            },
            delay=10,
        )
        return scraper
    except Exception as e:
        st.warning(f"CloudScraper não disponível: {e}. Usando requests.")
        return requests.Session()

scraper = create_advanced_scraper()

def fazer_requisicao_inteligente(url, max_tentativas=3):
    """Sistema inteligente de requisições com múltiplas estratégias"""
    cache_key = f"req_{hash(url)}"
    cached = cache.get(cache_key)
    if cached:
        return cached
    
    for tentativa in range(max_tentativas):
        try:
            # Delay progressivo entre tentativas
            if tentativa > 0:
                delay = tentativa * 2 + random.uniform(1, 3)
                time.sleep(delay)
                st.info(f"🔄 Tentativa {tentativa + 1} para {url.split('/')[-1][:50]}...")
            
            headers = get_dynamic_headers(url)
            
            # Tentar com CloudScraper primeiro
            response = scraper.get(url, headers=headers, timeout=25)
            
            if response.status_code == 200:
                # Verificar se não é uma página de bloqueio
                content_lower = response.text.lower()
                if not any(term in content_lower for term in ['access denied', 'blocked', 'bot detected', 'captcha']):
                    cache.set(cache_key, response)
                    return response
            
            # Se falhou, tentar com requests simples
            session = requests.Session()
            alt_headers = headers.copy()
            alt_headers['user-agent'] = random.choice([
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0'
            ])
            
            response = session.get(url, headers=alt_headers, timeout=20)
            if response.status_code == 200:
                cache.set(cache_key, response)
                return response
                
        except requests.exceptions.Timeout:
            st.warning(f"⏰ Timeout na tentativa {tentativa + 1}")
            continue
        except requests.exceptions.ConnectionError:
            st.warning(f"🔌 Erro de conexão na tentativa {tentativa + 1}")
            continue
        except Exception as e:
            st.warning(f"⚠️ Erro na tentativa {tentativa + 1}: {str(e)[:100]}...")
            continue
    
    return None

# ---------------------------
# SISTEMA DE BUSCA APRIMORADO
# ---------------------------
def buscar_via_api_zendesk(query, max_results=5):
    """Busca usando a API oficial do Zendesk (método mais confiável)"""
    cache_key = f"api_search_{hash(query)}"
    cached = cache.get(cache_key)
    if cached:
        return cached
    
    try:
        base_url = "https://centraldeatendimento.totvs.com/api/v2/help_center/pt-br/articles/search"
        params = {'query': query, 'per_page': max_results}
        
        headers = get_dynamic_headers()
        headers['accept'] = 'application/json'
        
        response = requests.get(base_url, params=params, headers=headers, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            articles = data.get('results', [])
            
            links = []
            for article in articles:
                url = article.get('html_url')
                if url and url not in links:
                    links.append(url)
            
            cache.set(cache_key, links)
            return links
            
    except Exception as e:
        st.warning(f"API Zendesk não disponível: {e}")
    
    return []

def extrair_conteudo_via_api(url):
    """Extrai conteúdo via API - método mais confiável"""
    try:
        article_id = re.search(r'/articles/(\d+)', url)
        if not article_id:
            return None
            
        article_id = article_id.group(1)
        api_url = f"https://centraldeatendimento.totvs.com/api/v2/help_center/pt-br/articles/{article_id}"
        
        headers = get_dynamic_headers()
        headers['accept'] = 'application/json'
        
        response = requests.get(api_url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            article = data.get('article', {})
            
            body = article.get('body', '')
            title = article.get('title', '')
            
            soup = BeautifulSoup(body, 'html.parser')
            text = soup.get_text(separator=' ', strip=True)
            
            full_content = f"{title}\n\n{text}"
            return clean_text(full_content)[:6000]
            
    except Exception:
        pass
    
    return None

# ---------------------------
# STOP WORDS E PRÉ-PROCESSAMENTO (MELHORADO)
# ---------------------------
STOP_WORDS = {
    "bom dia", "boa tarde", "boa noite", "olá", "att", "atenciosamente",
    "cumprimentos", "obrigado", "obrigada", "prezado", "prezada",
    "caro", "cara", "senhor", "senhora", "ola", "oi", "saudações",
    "tudo bem", "tudo bem?", "amigo", "amiga", "por favor",
    "grato", "grata", "cordialmente", "abraço", "abs", "ok", "entendi",
    "obg", "vlw", "por favor", "favor", "gostaria", "queria", "saber"
}

PALAVRAS_TECNICAS = {
    'erp', 'sql', 'api', 'xml', 'json', 'tss', 'nt', 'danfe', 'nfe', 'cte',
    'mde', 'sped', 'ecd', 'ecf', 'efd', 'protheus', 'fluig', 'rm', 'log',
    'fis', 'fat', 'crm', 'com', 'tms', 'wms', 'bi', 'linx', 'datasul'
}

def clean_query(query: str) -> str:
    """Limpa e otimiza a query para busca"""
    if not query:
        return ""
    
    # Remover caracteres especiais mas manter acentos
    query = re.sub(r'[^\w\sáàâãéèêíïóôõöúçñÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇÑ-]', ' ', query)
    query = query.lower().strip()
    
    # Remover stop words mas manter palavras técnicas
    parts = query.split()
    keep = []
    
    for p in parts:
        p_clean = p.strip()
        if (p_clean not in STOP_WORDS and len(p_clean) >= 2) or p_clean in PALAVRAS_TECNICAS:
            keep.append(p_clean)
    
    # Adicionar "Protheus" se não estiver presente e for uma consulta técnica
    if keep and "protheus" not in " ".join(keep).lower():
        termos_tecnicos = any(term in " ".join(keep).lower() for term in 
                            ['configurar', 'parâmetro', 'erro', 'funcionalidade', 'módulo'])
        if termos_tecnicos:
            keep.append("protheus")
    
    return " ".join(keep)

def clean_text(text: str) -> str:
    """Limpa texto extraído com algoritmos melhorados"""
    if not text or pd.isna(text):
        return ""
    
    # Remover caracteres nulos e problemas de encoding
    text = text.replace("\0", " ").replace("\r", " ").replace("\t", " ")
    
    # Remover padrões comuns de lixo
    patterns = [
        r'Anexo\(s\):.*',
        r'Compartilhar:.*',
        r'Comentários.*',
        r'Artigo criado.*Artigo atualizado.*',
        r'©\s*\d{4}.*TOTVS',
        r'https?://\S+',
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b'
    ]
    
    for pattern in patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.DOTALL)
    
    # Remover HTML tags
    text = re.sub(r'<[^>]*>', ' ', text)
    
    # Normalizar espaços
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def tem_video_ou_anexo(query: str) -> bool:
    """Verifica se a query se refere a conteúdo multimídia"""
    padroes = [
        r"\banexo\b", r"\banexos\b", r"\banexado\b", r"\banexada\b",
        r"\bv[íi]deo\b", r"\bv[íi]deos\b", r"\bgravaç[ãa]o\b",
        r"\bprint\b", r"\bimagem\b", r"\bscreenshot\b", r"\bfoto\b",
        r"\bpdf\b", r"\barquivo\b", r"\bdownload\b"
    ]
    query_lower = query.lower()
    return any(re.search(p, query_lower) for p in padroes)

# ---------------------------
# SISTEMA DE EXTRAÇÃO MELHORADO
# ---------------------------
def extrair_conteudo_pagina(url: str) -> str:
    """Extrai conteúdo com múltiplas estratégias"""
    if '/search?' in url:
        return "Página de pesquisa - conteúdo não extraído"

    # Tentar via API primeiro (método mais confiável)
    conteudo_api = extrair_conteudo_via_api(url)
    if conteudo_api:
        return conteudo_api

    # Fallback para scraping tradicional
    try:
        response = fazer_requisicao_inteligente(url)
        
        if not response:
            return f"❌ Não foi possível acessar: {url}"
            
        if response.status_code != 200:
            return f"Erro HTTP {response.status_code}: {url}"

        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remover elementos desnecessários
        for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', 'form', 'iframe']):
            element.decompose()
        
        # Estratégias de seleção melhoradas
        content_selectors = [
            "article",
            ".article-body",
            ".article-content", 
            "main",
            ".content",
            ".post-content",
            "[role='main']",
            ".help-center-content"
        ]
        
        content = None
        for selector in content_selectors:
            content = soup.select_one(selector)
            if content:
                break
        
        # Limpar elementos específicos
        if content:
            cleanup_selectors = [
                '.article-meta', '.article-info', '.article-votes',
                '.comments', '.share-buttons', '.breadcrumb',
                '.related-articles', '.article-attachments'
            ]
            
            for selector in cleanup_selectors:
                for element in content.select(selector):
                    element.decompose()
            
            text = content.get_text(separator=' ', strip=True)
        else:
            # Fallback estratégico
            body = soup.find('body')
            text = body.get_text(separator=' ', strip=True) if body else soup.get_text(separator=' ', strip=True)
        
        cleaned_text = clean_text(text)
        return cleaned_text[:6000] if cleaned_text else "Conteúdo não encontrado"
        
    except Exception as e:
        return f"Erro na extração: {str(e)}"

def pesquisar_interna_totvs(query: str, limit: int = 5) -> List[str]:
    """Pesquisa interna com fallbacks"""
    cache_key = f"internal_search_{hash(query)}"
    cached = cache.get(cache_key)
    if cached:
        return cached
    
    base = "https://centraldeatendimento.totvs.com"
    search_url = f"{base}/hc/pt-br/search?query={urllib.parse.quote(query)}"
    
    links = []
    try:
        response = fazer_requisicao_inteligente(search_url)
        
        if response and response.status_code == 200:
            soup = BeautifulSoup(response.content, "html.parser")
            
            # Múltiplos seletores para robustez
            selectors = [
                "a[href*='/articles/']",
                ".search-result a",
                ".article-list a",
                ".article-link"
            ]
            
            for selector in selectors:
                for a in soup.select(selector):
                    href = a.get("href", "")
                    if href:
                        if href.startswith("/"):
                            href = base + href
                        elif not href.startswith("http"):
                            href = base + "/" + href.lstrip("/")
                            
                        if href.startswith(base) and "/articles/" in href and href not in links:
                            links.append(href)
                            
                    if len(links) >= limit:
                        break
                if len(links) >= limit:
                    break
                    
    except Exception as e:
        st.warning(f"Pesquisa interna falhou: {e}")
    
    cache.set(cache_key, links)
    return links

def buscar_documentacao_totvs(query: str, max_links: int = 5) -> List[str]:
    """Sistema híbrido de busca com múltiplas fontes"""
    cache_key = f"search_{hash(query)}"
    cached = cache.get(cache_key)
    if cached:
        return cached
    
    cleaned = clean_query(query)
    if not cleaned:
        return []
    
    found = []
    seen = set()
    
    # Estratégia 1: API Zendesk (mais confiável)
    api_links = buscar_via_api_zendesk(cleaned, max_links)
    for url in api_links:
        if url not in seen:
            found.append(url)
            seen.add(url)
    
    # Estratégia 2: DuckDuckGo
    if len(found) < max_links:
        try:
            search_query = f"site:centraldeatendimento.totvs.com {cleaned}"
            with DDGS() as ddgs:
                for r in ddgs.text(search_query, max_results=10):
                    url = r.get("href", "")
                    if (url.startswith("https://centraldeatendimento.totvs.com") and 
                        "/articles/" in url and url not in seen):
                        found.append(url)
                        seen.add(url)
                    if len(found) >= max_links:
                        break
        except Exception as e:
            st.warning(f"DuckDuckGo falhou: {e}")
    
    # Estratégia 3: Pesquisa interna
    if len(found) < max_links:
        interna_links = pesquisar_interna_totvs(cleaned, max_links - len(found))
        for url in interna_links:
            if url not in seen:
                found.append(url)
                seen.add(url)
    
    # Fallback final
    if not found:
        found = [f"https://centraldeatendimento.totvs.com/hc/pt-br/search?query={urllib.parse.quote(cleaned)}"]
    
    cache.set(cache_key, found)
    return found[:max_links]

# ---------------------------
# SISTEMA DE RELEVÂNCIA MELHORADO
# ---------------------------
def pontuar_relevancia(texto: str, query: str) -> float:
    """Sistema de pontuação de relevância melhorado"""
    if not texto or not query:
        return 0.0
    
    tokens_query = set(clean_query(query).split())
    tokens_texto = set(texto.lower().split())
    
    if not tokens_query or not tokens_texto:
        return 0.0
    
    # Pontuação baseada na interseção
    intersection = tokens_query & tokens_texto
    base_score = len(intersection) / len(tokens_query)
    
    # Bônus para correspondências exatas
    exact_matches = sum(1 for token in tokens_query if token in texto.lower())
    exact_bonus = exact_matches * 0.1
    
    # Bônus para palavras técnicas
    tech_bonus = sum(0.05 for token in intersection if token in PALAVRAS_TECNICAS)
    
    final_score = min(base_score + exact_bonus + tech_bonus, 1.0)
    return final_score

# ---------------------------
# SISTEMA IA (MANTIDO COM PEQUENAS MELHORIAS)
# ---------------------------
def reclassificar_artigos_ia(artigos: List[Tuple[float, str, str]], query: str, use_gemini: bool, api_key: str, modelo: str) -> List[Tuple[float, str, str]]:
    if not artigos or len(artigos) <= 1:
        return artigos
    
    cache_key = f"reclass_{hash(query + ''.join(url for _, url, _ in artigos))}"
    cached = cache.get(cache_key)
    if cached:
        return cached
    
    try:
        artigos_info = []
        for score, url, conteudo in artigos:
            titulo = url.split('/')[-1].replace('-', ' ')[:100]
            preview = conteudo[:200] + "..." if conteudo and len(conteudo) > 50 else "Conteúdo não disponível"
            artigos_info.append(f"URL: {url}\nTítulo: {titulo}\nConteúdo: {preview}\n---")
        
        artigos_texto = "\n".join(artigos_info)
        
        if use_gemini:
            resposta = reclassificar_gemini(query, artigos_texto, modelo, api_key)
        else:
            resposta = reclassificar_openai(query, artigos_texto, modelo, api_key)
        
        artigos_ordenados = processar_resposta_reclassificacao(resposta, artigos)
        
        if artigos_ordenados:
            cache.set(cache_key, artigos_ordenados)
            return artigos_ordenados
        else:
            resultado = sorted(artigos, reverse=True, key=lambda x: x[0])
            cache.set(cache_key, resultado)
            return resultado
            
    except Exception as e:
        st.error(f"Erro na reclassificação por IA: {e}")
        resultado = sorted(artigos, reverse=True, key=lambda x: x[0])
        cache.set(cache_key, resultado)
        return resultado

# ... (mantenha as funções reclassificar_gemini, reclassificar_openai, 
# processar_resposta_reclassificacao, get_ai_response, get_gemini_response, 
# get_chatgpt_response do código original)

# ---------------------------
# INTERFACE STREAMLIT MELHORADA
# ---------------------------
def inicializar_session_state():
    """Inicializa as variáveis de session state"""
    defaults = {
        'min_score': 0.3,  # Score mais baixo para mais resultados
        'use_gemini': True,
        'modelo': "gemini-1.5-flash", 
        'api_key': "",
        'temperatura': 0.1,  # Temperatura mais baixa para precisão
        'mostrar_codigo': False,
        'reclassificar_ia': True,
        'cache_enabled': True,
        'historico': []
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def atualizar_lista_modelos():
    """Atualiza a lista de modelos baseado na escolha Gemini/OpenAI"""
    if st.session_state.use_gemini:
        modelos_disponiveis = ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-pro"]
        if st.session_state.modelo not in modelos_disponiveis:
            st.session_state.modelo = "gemini-1.5-flash"
    else:
        modelos_disponiveis = ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"]
        if not any(model in st.session_state.modelo for model in ["gpt", "openai"]):
            st.session_state.modelo = "gpt-4o-mini"
    return modelos_disponiveis

def adicionar_ao_historico(pergunta, resposta):
    """Adiciona interação ao histórico"""
    if 'historico' not in st.session_state:
        st.session_state.historico = []
    
    st.session_state.historico.append({
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'pergunta': pergunta,
        'resposta': resposta[:500] + "..." if len(resposta) > 500 else resposta
    })
    
    # Manter apenas os últimos 10 itens
    if len(st.session_state.historico) > 10:
        st.session_state.historico = st.session_state.historico[-10:]

# ... (mantenha as funções formatar_links_saiba_mais, processar_pergunta, 
# e main do código original, mas atualize a sidebar com novas opções)

# NA FUNÇÃO MAIN, ATUALIZE A SIDEBAR:
def main():
    inicializar_session_state()
    
    with st.sidebar:
        st.header("⚙️ Configurações Avançadas")
        
        # Configurações básicas
        st.session_state.use_gemini = st.checkbox(
            "Usar Google Gemini", 
            value=st.session_state.use_gemini,
            help="Desmarque para usar OpenAI"
        )
        
        modelos_disponiveis = atualizar_lista_modelos()
        
        # Configurações de performance
        st.subheader("🚀 Performance")
        
        st.session_state.cache_enabled = st.checkbox(
            "Ativar Cache", 
            value=st.session_state.cache_enabled,
            help="Melhora performance armazenando resultados temporariamente"
        )
        
        if st.button("🧹 Limpar Cache"):
            cache.clear()
            st.success("Cache limpo!")
        
        st.session_state.reclassificar_ia = st.checkbox(
            "Reclassificação por IA", 
            value=st.session_state.reclassificar_ia,
            help="Usa IA para ordenar resultados por relevância"
        )
        
        st.session_state.min_score = st.slider(
            "Score Mínimo de Relevância",
            min_value=0.0,
            max_value=1.0,
            value=st.session_state.min_score,
            step=0.05,
            help="Valores mais baixos retornam mais resultados"
        )
        
        st.session_state.temperatura = st.slider(
            "Temperatura da IA",
            min_value=0.0,
            max_value=1.0,
            value=st.session_state.temperatura,
            step=0.1,
            help="0 = preciso, 1 = criativo"
        )
        
        # Modelo e API
        st.session_state.modelo = st.selectbox(
            "Modelo de IA",
            options=modelos_disponiveis,
            index=modelos_disponiveis.index(st.session_state.modelo)
        )
        
        st.session_state.api_key = st.text_input(
            "Chave da API",
            value=st.session_state.api_key,
            type="password",
            placeholder="Cole sua chave da API aqui"
        )
        
        # Histórico
        if st.session_state.get('historico'):
            st.subheader("📚 Histórico")
            for i, item in enumerate(reversed(st.session_state.historico[-5:])):
                with st.expander(f"{item['timestamp']} - {item['pergunta'][:50]}..."):
                    st.write(f"**P:** {item['pergunta']}")
                    st.write(f"**R:** {item['resposta']}")
        
        st.markdown("---")
        st.info("""
        **💡 Dicas:**
        - Use termos técnicos específicos
        - Score 0.2-0.4 para mais resultados
        - Ative o cache para melhor performance
        """)

# ... (restante do código main mantido igual)

if __name__ == "__main__":
    main()
