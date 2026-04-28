import streamlit as st
import streamlit.components.v1 as components
import requests
import json
import pandas as pd
from datetime import datetime, timedelta
import io
import base64
from PIL import Image, ImageDraw, ImageFont
import re
import time
import plotly.express as px
import plotly.graph_objects as go
from bs4 import BeautifulSoup
import urllib.parse
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import xlsxwriter
from io import BytesIO
import hashlib
import random
from collections import defaultdict
import calendar as cal_module
from colorthief import ColorThief
import webcolors
import os

# =========================
# Configuration (set via env vars or Streamlit secrets)
# =========================
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY", "")
GROQ_MODEL = "llama-3.3-70b-versatile"

# Hugging Face model (Router endpoint supports this)
HUGGINGFACE_IMAGE_MODEL = "black-forest-labs/FLUX.1-schnell"

# Campaign Database
CAMPAIGN_DATABASE = "campaign_database.xlsx"

# =========================
# Multi-language support
# =========================
LANGUAGES = {
    'English': 'en', 'Spanish': 'es', 'French': 'fr', 'German': 'de',
    'Italian': 'it', 'Portuguese': 'pt', 'Hindi': 'hi', 'Chinese': 'zh',
    'Japanese': 'ja', 'Korean': 'ko'
}

# =========================
# Platform specifications
# =========================
PLATFORM_SPECS = {
    'Instagram': {
        'max_length': 2200, 'hashtag_limit': 30, 'image_ratio': '1:1',
        'optimal_length': 125, 'hashtag_suggestions': ['#instagram', '#insta', '#marketing', '#brand']
    },
    'Twitter': {
        'max_length': 280, 'hashtag_limit': 2, 'image_ratio': '16:9',
        'optimal_length': 140, 'hashtag_suggestions': ['#twitter', '#marketing', '#brand']
    },
    'Facebook': {
        'max_length': 63206, 'hashtag_limit': 5, 'image_ratio': '1.91:1',
        'optimal_length': 80, 'hashtag_suggestions': ['#facebook', '#social', '#marketing']
    },
    'LinkedIn': {
        'max_length': 3000, 'hashtag_limit': 3, 'image_ratio': '1.91:1',
        'optimal_length': 150, 'hashtag_suggestions': ['#linkedin', '#professional', '#business']
    },
    'TikTok': {
        'max_length': 2200, 'hashtag_limit': 20, 'image_ratio': '9:16',
        'optimal_length': 100, 'hashtag_suggestions': ['#tiktok', '#viral', '#trending']
    },
    'YouTube': {
        'max_length': 5000, 'hashtag_limit': 15, 'image_ratio': '16:9',
        'optimal_length': 200, 'hashtag_suggestions': ['#youtube', '#video', '#content']
    }
}

# =========================
# Campaign Templates
# =========================
CAMPAIGN_TEMPLATES = {
    'Product Launch': {
        'description': 'Perfect for announcing new products or services',
        'content_types': ['social_media_posts', 'ad_copy', 'email_campaigns'],
        'tone': 'Excited',
        'platforms': ['Instagram', 'Facebook', 'Twitter'],
        'duration_days': 7
    },
    'Brand Awareness': {
        'description': 'Build recognition and establish brand identity',
        'content_types': ['social_media_posts', 'blog_content'],
        'tone': 'Professional',
        'platforms': ['LinkedIn', 'Facebook', 'Instagram'],
        'duration_days': 14
    },
    'Seasonal Campaign': {
        'description': 'Holiday or seasonal promotional content',
        'content_types': ['social_media_posts', 'ad_copy', 'email_campaigns'],
        'tone': 'Friendly',
        'platforms': ['Instagram', 'Facebook', 'TikTok'],
        'duration_days': 10
    },
    'Educational Series': {
        'description': 'Share knowledge and establish thought leadership',
        'content_types': ['blog_content', 'social_media_posts'],
        'tone': 'Authoritative',
        'platforms': ['LinkedIn', 'YouTube', 'Facebook'],
        'duration_days': 21
    },
    'Customer Engagement': {
        'description': 'Interactive content to boost engagement',
        'content_types': ['social_media_posts'],
        'tone': 'Casual',
        'platforms': ['Instagram', 'TikTok', 'Twitter'],
        'duration_days': 5
    },
    'Event Promotion': {
        'description': 'Promote webinars, conferences, or events',
        'content_types': ['social_media_posts', 'email_campaigns', 'ad_copy'],
        'tone': 'Professional',
        'platforms': ['LinkedIn', 'Facebook', 'Twitter'],
        'duration_days': 14
    }
}

# =========================
# Core class
# =========================
class SmartAICampaignGenerator:

    def __init__(self):
        self.groq_api_key = GROQ_API_KEY
        self.hf_api_key = HUGGINGFACE_API_KEY
        if 'campaigns' not in st.session_state:
            st.session_state.campaigns = []

    # --------- Chat / Content ---------

    def ai_chat_assistant(self, message, context=False):
        try:
            if not self.groq_api_key or self.groq_api_key == "YOUR_GROQ_API_KEY":
                return "[AI Assistant] No Groq API key configured."
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.groq_api_key}",
                "Content-Type": "application/json"
            }
            data = {
                "model": GROQ_MODEL,
                "messages": [
                    {"role": "system", "content": "You are a helpful AI marketing assistant."},
                    {"role": "user", "content": message}
                ],
                "max_tokens": 256,
                "temperature": 0.7
            }
            response = requests.post(url, headers=headers, json=data, timeout=20)
            response.raise_for_status()
            result = response.json()
            return result['choices'][0]['message']['content'].strip()
        except Exception as e:
            return f"[AI Assistant] Error: {e}"

    def generate_content_with_groq(self, prompt, max_tokens=3000):
        try:
            if not self.groq_api_key or self.groq_api_key == "YOUR_GROQ_API_KEY":
                return self.generate_fallback_content(prompt)
            headers = {
                'Authorization': f'Bearer {self.groq_api_key}',
                'Content-Type': 'application/json'
            }
            payload = {
                'model': GROQ_MODEL,
                'messages': [{'role': 'user', 'content': prompt}],
                'max_tokens': max_tokens,
                'temperature': 0.7
            }
            response = requests.post(
                'https://api.groq.com/openai/v1/chat/completions',
                headers=headers,
                json=payload,
                timeout=30
            )
            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content']
            elif response.status_code == 402:
                st.warning("⚠️ Groq API credits exceeded. Using fallback...")
                return self.generate_fallback_content(prompt)
            else:
                return self.generate_fallback_content(prompt)
        except Exception:
            return self.generate_fallback_content(prompt)

    def generate_fallback_content(self, prompt):
        content_type = self._detect_content_type(prompt)
        brand_name = self._extract_brand_from_prompt(prompt)
        templates = self._get_content_templates()
        selected_templates = templates.get(content_type, templates['social_media'])
        customized_content = []
        for template in selected_templates:
            customized = template.replace("{brand_name}", brand_name)
            customized_content.append(customized)
        return "\n\n---VARIANT 2---\n\n".join(customized_content)

    def _detect_content_type(self, prompt):
        prompt_lower = prompt.lower()
        if 'social media' in prompt_lower:
            return 'social_media'
        elif 'ad copy' in prompt_lower or 'advertisement' in prompt_lower:
            return 'ad_copy'
        elif 'email' in prompt_lower:
            return 'email'
        elif 'blog' in prompt_lower:
            return 'blog'
        return 'social_media'

    def _extract_brand_from_prompt(self, prompt):
        if "Brand:" in prompt:
            try:
                brand_line = prompt.split("Brand:")[1].split("\n")[0].strip()
                return brand_line if brand_line else "Your Brand"
            except:
                pass
        return "Your Brand"

    def _get_content_templates(self):
        return {
            'social_media': [
                "🌟 Exciting news from {brand_name}! We're launching something incredible. #Innovation #Quality",
                "✨ At {brand_name}, we believe in excellence. #CustomerFirst #Excellence",
                "🚀 Ready for the {brand_name} difference? Join us! #GameChanger"
            ],
            'ad_copy': [
                "**Headline:** Transform with {brand_name}\n**Description:** Quality & service.\n**CTA:** Get Started!",
            ],
            'email': [
                "**Subject:** Welcome to {brand_name}! 🎉\n\nWelcome! Explore our features.\n\nBest,\n{brand_name}",
            ],
            'blog': [
                "**Title:** Complete Guide with {brand_name}\n\n**Key Points:**\n• Understanding needs\n• Implementation\n• Success metrics",
            ]
        }

    def generate_campaign_content(self, brand_info, content_type, tone, language, sentiment):
        prompt = f"""
        Create {content_type.replace('_', ' ')} for:
        
        Brand: {brand_info.get('brand_name', 'Brand')}
        Description: {brand_info.get('description', '')}
        Tone: {tone}
        Sentiment: {sentiment}
        
        Generate professional content with clear CTA.
        """
        return self.generate_content_with_groq(prompt)

    def get_all_templates(self):
        templates = dict(CAMPAIGN_TEMPLATES)
        if 'saved_templates' in st.session_state:
            for t in st.session_state.saved_templates:
                if isinstance(t, dict) and 'name' in t:
                    templates[t['name']] = t
        return templates

    # --------- Website extraction / style guide ---------

    def generate_brand_style_guide(self, brand_data, website_url):
        style_guide = {}
        # Colors
        colors = {}
        if brand_data and 'images' in brand_data and brand_data['images']:
            for img in brand_data['images']:
                img_url = img.get('url')
                if img_url:
                    try:
                        img_resp = requests.get(img_url, timeout=5)
                        img_resp.raise_for_status()
                        img_bytes = BytesIO(img_resp.content)
                        color_thief = ColorThief(img_bytes)
                        dominant_color = color_thief.get_color(quality=1)
                        hex_color = webcolors.rgb_to_hex(dominant_color)
                        colors[img_url] = hex_color
                    except Exception:
                        continue
        style_guide['colors'] = colors

        # Typography
        try:
            resp = requests.get(website_url, timeout=10)
            soup = BeautifulSoup(resp.text, 'html.parser')
            fonts = set()
            for style in soup.find_all('style'):
                if style.string:
                    matches = re.findall(r'font-family:\s*([^;\n]+)', style.string)
                    for match in matches:
                        fonts.add(match.strip().strip('"\''))
            style_guide['typography'] = list(fonts)
        except Exception:
            style_guide['typography'] = []

        # Voice/Tone
        voice = ''
        if brand_data:
            desc = brand_data.get('description', '').lower()
            if 'friendly' in desc:
                voice = 'Friendly'
            elif 'professional' in desc:
                voice = 'Professional'
            elif 'excited' in desc:
                voice = 'Excited'
            elif 'authoritative' in desc:
                voice = 'Authoritative'
            elif 'casual' in desc:
                voice = 'Casual'
            else:
                voice = 'General'
        style_guide['voice_tone'] = voice

        # Principles
        style_guide['design_principles'] = ['Consistency', 'Clarity', 'Accessibility', 'Simplicity']

        st.session_state.brand_style_guide = style_guide
        return style_guide

    def extract_website_info(self, url):
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            brand_name = urllib.parse.urlparse(url).netloc.replace('www.', '').split('.')[0]
            og_title = soup.find('meta', property='og:title')
            if og_title:
                brand_name = og_title.get('content', brand_name)

            description = self._extract_description(soup)
            images = self._extract_images(soup, url)
            social_links = self._extract_social_links(soup)
            keywords = self._extract_keywords(soup)
            contact_info = self._extract_contact_info(soup)

            industry = ''
            og_type = soup.find('meta', property='og:type')
            if og_type:
                industry = og_type.get('content', '')

            return {
                'brand_name': brand_name,
                'description': description,
                'images': images,
                'social_links': social_links,
                'keywords': keywords,
                'contact_info': contact_info,
                'industry': industry,
                'url': url
            }
        except Exception as e:
            st.warning(f"Failed to extract website info: {e}")
            return None

    def _extract_description(self, soup):
        description = ""
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc:
            description = meta_desc.get('content', '')
        og_desc = soup.find('meta', property='og:description')
        if og_desc and not description:
            description = og_desc.get('content', '')
        return description

    def _extract_images(self, soup, url):
        images = []
        logo_imgs = soup.find_all('img', src=True, alt=re.compile(r'logo', re.I))
        for img in logo_imgs[:3]:
            img_src = self._resolve_url(img['src'], url)
            if img_src:
                images.append({'type': 'logo', 'url': img_src, 'alt': img.get('alt', '')})
        general_imgs = soup.find_all('img', src=True)[:10]
        for img in general_imgs:
            img_src = self._resolve_url(img['src'], url)
            if img_src and not any(i['url'] == img_src for i in images):
                images.append({'type': 'general', 'url': img_src, 'alt': img.get('alt', '')})
        return images[:15]

    def _extract_social_links(self, soup):
        social_links = {}
        social_patterns = {
            'facebook': r'facebook\.com',
            'twitter': r'twitter\.com|x\.com',
            'instagram': r'instagram\.com',
            'linkedin': r'linkedin\.com',
            'youtube': r'youtube\.com',
            'tiktok': r'tiktok\.com'
        }
        links = soup.find_all('a', href=True)
        for link in links:
            href = link['href']
            for platform, pattern in social_patterns.items():
                if re.search(pattern, href, re.I):
                    social_links[platform] = href
                    break
        return social_links

    def _extract_keywords(self, soup):
        keywords = []
        meta_keywords = soup.find('meta', attrs={'name': 'keywords'})
        if meta_keywords:
            keywords.extend([kw.strip() for kw in meta_keywords.get('content', '').split(',')])
        headings = soup.find_all(['h1', 'h2', 'h3'])
        for h in headings:
            text = h.get_text().strip()
            if text and len(text) < 100:
                keywords.append(text)
        return list(set(keywords))[:20]

    def _extract_contact_info(self, soup):
        contact_info = {}
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, soup.get_text())
        if emails:
            contact_info['emails'] = list(set(emails))[:5]
        return contact_info

    def _resolve_url(self, url, base_url):
        if url.startswith('//'):
            return 'https:' + url
        elif url.startswith('/'):
            return urllib.parse.urljoin(base_url, url)
        elif url.startswith('http'):
            return url
        return None

    # --------- Competitor analysis ---------

    def analyze_competitors(self, brand_name, industry, competitor_urls=None):
        prompt = f"""
        Perform comprehensive competitor analysis for {brand_name} in {industry}.
        
        Provide:
        1. Top 5 competitors
        2. Market positioning
        3. Content opportunities
        4. Unique selling points
        5. Trending strategies
        6. Action items
        """
        analysis = self.generate_content_with_groq(prompt)
        competitor_insights = {}
        if competitor_urls:
            for url in competitor_urls:
                try:
                    competitor_data = self.extract_website_info(url)
                    if competitor_data:
                        competitor_insights[url] = competitor_data
                except Exception as e:
                    st.warning(f"Could not analyze {url}: {str(e)}")
        st.session_state.competitor_data = {
            'analysis': analysis,
            'competitor_websites': competitor_insights,
            'timestamp': datetime.now()
        }
        return analysis

    # --------- Image generation (HF) ---------

    def _fit_image_to_platform(self, image_bytes, platform):
        ratio_str = PLATFORM_SPECS.get(platform, {}).get('image_ratio', '1:1')
        try:
            a, b = ratio_str.split(':')
            target_ratio = float(a) / float(b)
        except Exception:
            target_ratio = 1.0

        im = Image.open(BytesIO(image_bytes)).convert("RGB")
        w, h = im.size
        current_ratio = w / h

        if abs(current_ratio - target_ratio) < 1e-3:
            out = im
        elif current_ratio > target_ratio:
            new_w = int(h * target_ratio)
            x1 = (w - new_w) // 2
            out = im.crop((x1, 0, x1 + new_w, h))
        else:
            new_h = int(w / target_ratio)
            y1 = (h - new_h) // 2
            out = im.crop((0, y1, w, y1 + new_h))

        target_sizes = {
            '1:1': (768, 768),
            '16:9': (960, 540),
            '9:16': (540, 960),
            '1.91:1': (1200, 628)
        }
        target_size = target_sizes.get(ratio_str, out.size)
        out = out.resize(target_size, Image.LANCZOS)

        buf = BytesIO()
        out.save(buf, format="PNG")
        return buf.getvalue()
    
    def generate_image_with_hf(self, prompt, style="professional", platform="Instagram", show_progress=True):
        try:
            enhanced_prompt = f"{prompt}, {style} style, high quality marketing image"

            if self.hf_api_key and self.hf_api_key != "YOUR_HUGGINGFACE_API_KEY":
                try:
                    image_bytes = self._generate_hf_image(enhanced_prompt)

                    # Optional resize
                    final_bytes = self._fit_image_to_platform(image_bytes, platform)
                    return final_bytes

                except Exception as api_error:
                    print("HF FAILED:", api_error)

            # Fallback
            return self._generate_placeholder_image(prompt, style, platform)

        except Exception as e:
            print("Unexpected error:", e)
            return self._generate_placeholder_image(prompt, style, platform)

    def _generate_hf_image(self, prompt, width=768, height=768):
        import requests

        url = f"https://router.huggingface.co/hf-inference/models/{HUGGINGFACE_IMAGE_MODEL}"

        headers = {
            "Authorization": f"Bearer {self.hf_api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "inputs": prompt
        }

        response = requests.post(url, headers=headers, json=payload)

        if response.status_code != 200:
            raise Exception(f"HF Error {response.status_code}: {response.text}")

        return response.content
    
    def _generate_placeholder_image(self, prompt, style, platform):
        specs = PLATFORM_SPECS.get(platform, PLATFORM_SPECS['Instagram'])
        if specs['image_ratio'] == '1:1':
            width, height = 512, 512
        elif specs['image_ratio'] == '16:9':
            width, height = 512, 288
        elif specs['image_ratio'] == '9:16':
            width, height = 288, 512
        elif specs['image_ratio'] == '1.91:1':
            width, height = 600, 314
        else:
            width, height = 512, 288

        img = Image.new('RGB', (width, height), color='white')
        draw = ImageDraw.Draw(img)
        for i in range(height):
            color = int(255 * (1 - i / height * 0.3))
            draw.line([(0, i), (width, i)], fill=(color, min(color + 10, 255), min(color + 20, 255)))
        draw.rectangle([10, 10, width-10, height-10], outline='#2E86AB', width=3)
        font = ImageFont.load_default()
        lines = [
            f"AI Generated Image",
            f"Platform: {platform}",
            f"Style: {style}",
            prompt[:30] + "..." if len(prompt) > 30 else prompt
        ]
        y = height // 2 - 40
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            text_width = bbox[2] - bbox[0]
            x = (width - text_width) // 2
            draw.text((x, y), line, fill='black', font=font)
            y += 20
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='PNG')
        return img_byte_arr.getvalue()

    # --------- Campaign packaging ---------

    def create_campaign_package(self, brand_info, selected_content_types, selected_platforms,
                                tone, language, sentiment, target_audience="general", options=None):
        if options is None:
            options = {'generate_images': True, 'generate_ab_variants': True, 'generate_captions': True}

        campaign = {
            'id': hashlib.md5(f"{brand_info.get('brand_name', '')}{datetime.now()}".encode()).hexdigest()[:8],
            'brand_info': brand_info,
            'created_at': datetime.now(),
            'selected_platforms': selected_platforms,
            'content': {},
            'platform_content': {},
            'ab_variants': {},
            'images': {},
            'captions': {},
            'tone': tone,
            'language': language,
            'sentiment': sentiment,
            'target_audience': target_audience,
            'generation_options': options
        }

        total_steps = len(selected_content_types) * (1 + len(selected_platforms))
        if options.get('generate_ab_variants'): total_steps += len(selected_content_types)
        if options.get('generate_images'): total_steps += len(selected_content_types) * len(selected_platforms)

        progress_bar = st.progress(0)
        step = 0

        for content_type in selected_content_types:
            with st.spinner(f"Generating {content_type.replace('_', ' ')}..."):
                base_content = self.generate_campaign_content(brand_info, content_type, tone, language, sentiment)
                campaign['content'][content_type] = base_content
                step += 1
                progress_bar.progress(step / total_steps)

            campaign['platform_content'][content_type] = {}
            for platform in selected_platforms:
                platform_content = self.generate_platform_specific_content(base_content, platform, brand_info, target_audience)
                campaign['platform_content'][content_type][platform] = platform_content
                step += 1
                progress_bar.progress(step / total_steps)

            if options.get('generate_ab_variants'):
                ab_variants = self.generate_ab_variants(base_content, 3)
                campaign['ab_variants'][content_type] = ab_variants
                step += 1
                progress_bar.progress(step / total_steps)

            if options.get('generate_images'):
                campaign['images'][content_type] = {}
                campaign['captions'][content_type] = {}

                for platform in selected_platforms:
                    image_prompt = f"{brand_info.get('brand_name', 'Brand')} {content_type}"
                    image_data = self.generate_image_with_hf(image_prompt,tone.lower(),platform,False
)
                    campaign['images'][content_type][platform] = image_data

                    if options.get('generate_captions'):
                        caption = self.generate_caption_for_image(f"{content_type} image", brand_info, platform)
                        campaign['captions'][content_type][platform] = caption

                    step += 1
                    progress_bar.progress(step / total_steps)

        st.session_state.campaigns.append(campaign)
        if 'analytics_data' not in st.session_state:
            st.session_state.analytics_data = {}
        st.session_state.analytics_data[campaign['id']] = {'created': datetime.now(), 'performance': {}}

        progress_bar.progress(1.0)
        return campaign

    def generate_platform_specific_content(self, base_content, platform, brand_info, audience_type="general"):
        specs = PLATFORM_SPECS.get(platform, PLATFORM_SPECS['Facebook'])
        prompt = f"""
        Optimize for {platform}:
        
        Original: {base_content[:500]}
        Brand: {brand_info.get('brand_name', 'Brand')}
        
        Requirements:
        - Max {specs['max_length']} chars
        - Max {specs['hashtag_limit']} hashtags
        - Platform tone
        - CTA included
    """
        return self.generate_content_with_groq(prompt, max_tokens=500)

    def generate_ab_variants(self, base_content, variant_count=3):
        prompt = f"""
        Create {variant_count} A/B variants:
        
        Base: {base_content[:300]}
        
        Modify headlines, CTA, tone, value props.
        Label as Variant A, B, C.
        """
        return self.generate_content_with_groq(prompt, max_tokens=1000)

    def generate_caption_for_image(self, image_description, brand_info, platform="Instagram"):
        specs = PLATFORM_SPECS[platform]
        prompt = f"""
        Caption for:
        
        Image: {image_description}
        Brand: {brand_info.get('brand_name', 'Brand')}
        Platform: {platform}
        
        Engaging tone, max {specs['hashtag_limit']} hashtags, strong CTA.
        """
        return self.generate_content_with_groq(prompt, max_tokens=300)

    # --------- Scheduling / Analytics / Export / Feedback ---------

    def schedule_post(self, campaign_id, content_type, platform, scheduled_time, variant='base'):
        post = {
            'id': hashlib.md5(f"{campaign_id}{content_type}{platform}{scheduled_time}".encode()).hexdigest()[:8],
            'campaign_id': campaign_id,
            'content_type': content_type,
            'platform': platform,
            'scheduled_time': scheduled_time,
            'variant': variant,
            'status': 'scheduled',
            'created_at': datetime.now()
        }
        st.session_state.scheduled_posts.append(post)
        return post

    def simulate_performance_metrics(self, campaign_id, content_type, platform):
        base = random.randint(100, 10000)
        metrics = {
            'views': base * random.randint(10, 50),
            'clicks': int(base * random.uniform(0.02, 0.15)),
            'likes': int(base * random.uniform(0.05, 0.25)),
            'shares': int(base * random.uniform(0.01, 0.10)),
            'comments': int(base * random.uniform(0.01, 0.08)),
            'engagement_rate': round(random.uniform(2.5, 15.0), 2),
            'ctr': round(random.uniform(0.5, 5.0), 2)
        }

        if campaign_id in st.session_state.analytics_data:
            if 'performance' not in st.session_state.analytics_data[campaign_id]:
                st.session_state.analytics_data[campaign_id]['performance'] = {}
            if content_type not in st.session_state.analytics_data[campaign_id]['performance']:
                st.session_state.analytics_data[campaign_id]['performance'][content_type] = {}
            st.session_state.analytics_data[campaign_id]['performance'][content_type][platform] = metrics

        return metrics

    def generate_ab_test_results(self, campaign_id, content_type):
        variants = ['A', 'B', 'C']
        results = {}
        for variant in variants:
            results[f'Variant {variant}'] = {
                'engagement_rate': round(random.uniform(2.0, 15.0), 2),
                'click_through_rate': round(random.uniform(0.5, 5.0), 2),
                'conversion_rate': round(random.uniform(0.1, 3.0), 2)
            }
        winner = max(results.items(), key=lambda x: x[1]['engagement_rate'])[0]
        return {
            'results': results,
            'winner': winner,
            'confidence': round(random.uniform(85, 99), 1)
        }

    def _get_pdf_font_name(self):
        font_name = "DejaVuSans"
        if font_name in pdfmetrics.getRegisteredFontNames():
            return font_name

        font_paths = [
            "C:\\Windows\\Fonts\\seguiemj.ttf",
            "C:\\Windows\\Fonts\\DejaVuSans.ttf",
            "C:\\Windows\\Fonts\\Arial Unicode MS.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
            "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf",
        ]

        for path in font_paths:
            if os.path.exists(path):
                try:
                    pdfmetrics.registerFont(TTFont(font_name, path))
                    return font_name
                except Exception:
                    continue

        return "Helvetica"

    def _render_paragraph(self, text):
        safe_text = str(text)
        safe_text = safe_text.replace("&", "&amp;")
        safe_text = safe_text.replace("<", "&lt;")
        safe_text = safe_text.replace(">", "&gt;")
        safe_text = safe_text.replace("\n", "<br/>")
        return safe_text

    def export_campaign_to_pdf(self, campaign):
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=inch / 2,
            leftMargin=inch / 2,
            topMargin=inch / 2,
            bottomMargin=inch / 2,
        )
        story = []
        font_name = self._get_pdf_font_name()
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name="TitleUnicode", parent=styles["Title"], fontName=font_name))
        styles.add(ParagraphStyle(name="Heading2Unicode", parent=styles["Heading2"], fontName=font_name))
        styles.add(ParagraphStyle(name="BodyTextUnicode", parent=styles["BodyText"], fontName=font_name, leading=14))

        story.append(Paragraph(f"Campaign Report: {campaign['brand_info'].get('brand_name', 'Brand')}", styles["TitleUnicode"]))
        story.append(Spacer(1, 12))
        story.append(Paragraph(f"Campaign ID: {campaign['id']}", styles["BodyTextUnicode"]))
        story.append(Paragraph(f"Created: {campaign['created_at'].strftime('%Y-%m-%d %H:%M')}", styles["BodyTextUnicode"]))
        story.append(Spacer(1, 12))

        story.append(Paragraph("Campaign Overview", styles["Heading2Unicode"]))
        story.append(Spacer(1, 8))
        story.append(Paragraph(f"Brand: {campaign['brand_info'].get('brand_name', '')}", styles["BodyTextUnicode"]))
        description = campaign['brand_info'].get('description', '')
        if description:
            story.append(Paragraph(f"Description: {self._render_paragraph(description)}", styles["BodyTextUnicode"]))
        story.append(Paragraph(f"Selected Platforms: {', '.join(campaign.get('selected_platforms', []))}", styles["BodyTextUnicode"]))
        story.append(Paragraph(f"Tone: {campaign.get('tone', '')}", styles["BodyTextUnicode"]))
        story.append(Paragraph(f"Language: {campaign.get('language', '')}", styles["BodyTextUnicode"]))
        story.append(Paragraph(f"Sentiment: {campaign.get('sentiment', '')}", styles["BodyTextUnicode"]))
        story.append(Paragraph(f"Target Audience: {campaign.get('target_audience', '')}", styles["BodyTextUnicode"]))
        generation_options = campaign.get('generation_options', {})
        if generation_options:
            enabled = [k.replace('_', ' ').title() for k, v in generation_options.items() if v]
            story.append(Paragraph(f"Generation Options: {', '.join(enabled)}", styles["BodyTextUnicode"]))
        if campaign['brand_info'].get('images'):
            story.append(Paragraph(f"Website Images Found: {len(campaign['brand_info'].get('images', []))}", styles["BodyTextUnicode"]))
        story.append(Spacer(1, 12))

        def add_section(title):
            story.append(Paragraph(title, styles["Heading2Unicode"]))
            story.append(Spacer(1, 8))

        for content_type, content in campaign.get('content', {}).items():
            add_section(f"{content_type.replace('_', ' ').title()}")
            story.append(Paragraph(self._render_paragraph(content), styles["BodyTextUnicode"]))
            story.append(Spacer(1, 10))

            platform_content = campaign.get('platform_content', {}).get(content_type, {})
            if platform_content:
                story.append(Paragraph("Platform Specific Content", styles["Heading2Unicode"]))
                story.append(Spacer(1, 6))
                for platform, text in platform_content.items():
                    story.append(Paragraph(f"{platform}", styles["BodyTextUnicode"]))
                    story.append(Paragraph(self._render_paragraph(text), styles["BodyTextUnicode"]))
                    story.append(Spacer(1, 8))

            ab_variants = campaign.get('ab_variants', {}).get(content_type, {})
            if ab_variants:
                story.append(Paragraph("A/B Variants", styles["Heading2Unicode"]))
                story.append(Spacer(1, 6))
                if isinstance(ab_variants, dict):
                    for variant, variant_text in ab_variants.items():
                        story.append(Paragraph(f"{variant}", styles["BodyTextUnicode"]))
                        story.append(Paragraph(self._render_paragraph(variant_text), styles["BodyTextUnicode"]))
                        story.append(Spacer(1, 8))
                else:
                    story.append(Paragraph(self._render_paragraph(ab_variants), styles["BodyTextUnicode"]))
                    story.append(Spacer(1, 8))

            captions = campaign.get('captions', {}).get(content_type, {})
            if captions:
                story.append(Paragraph("Image Captions", styles["Heading2Unicode"]))
                story.append(Spacer(1, 6))
                table_data = [["Platform", "Caption"]]
                for platform, caption in captions.items():
                    table_data.append([platform, caption])
                table = Table(table_data, colWidths=[2.2 * inch, 4.3 * inch], repeatRows=1)
                table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4B8BBE")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (-1, -1), font_name),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.grey),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.black),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
                ]))
                story.append(table)
                story.append(Spacer(1, 12))

            story.append(PageBreak())

        if story and isinstance(story[-1], PageBreak):
            story.pop()

        doc.build(story)
        buffer.seek(0)
        return buffer

    def export_campaign_to_excel(self, campaign):
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            overview = pd.DataFrame({
                'Field': [
                    'Campaign ID',
                    'Brand',
                    'Created',
                    'Tone',
                    'Language',
                    'Sentiment',
                    'Target Audience',
                    'Selected Platforms',
                    'Generation Options',
                ],
                'Value': [
                    campaign['id'],
                    campaign['brand_info'].get('brand_name', ''),
                    campaign['created_at'].strftime('%Y-%m-%d %H:%M'),
                    campaign.get('tone', ''),
                    campaign.get('language', ''),
                    campaign.get('sentiment', ''),
                    campaign.get('target_audience', ''),
                    ', '.join(campaign.get('selected_platforms', [])),
                    ', '.join([k.replace('_', ' ').title() for k, v in campaign.get('generation_options', {}).items() if v]),
                ],
            })
            overview.to_excel(writer, sheet_name='Overview', index=False)

            brand_info_rows = []
            for key, value in campaign.get('brand_info', {}).items():
                if key == 'images':
                    continue
                brand_info_rows.append({'Field': key.replace('_', ' ').title(), 'Value': value})
            if campaign.get('brand_info', {}).get('images'):
                brand_info_rows.append({'Field': 'Website Images', 'Value': len(campaign['brand_info'].get('images', []))})
            brand_info = pd.DataFrame(brand_info_rows)
            brand_info.to_excel(writer, sheet_name='Brand Info', index=False)

            content_rows = []
            for content_type, content in campaign.get('content', {}).items():
                content_rows.append({
                    'Section': content_type.replace('_', ' ').title(),
                    'Platform': 'Base',
                    'Text': content,
                })
                platform_content = campaign.get('platform_content', {}).get(content_type, {})
                for platform, platform_text in platform_content.items():
                    content_rows.append({
                        'Section': content_type.replace('_', ' ').title(),
                        'Platform': platform,
                        'Text': platform_text,
                    })
            content_df = pd.DataFrame(content_rows)
            content_df.to_excel(writer, sheet_name='Content', index=False)

            ab_rows = []
            for content_type, variants in campaign.get('ab_variants', {}).items():
                if isinstance(variants, dict):
                    for variant, variant_text in variants.items():
                        ab_rows.append({
                            'Content Type': content_type.replace('_', ' ').title(),
                            'Variant': variant,
                            'Text': variant_text,
                        })
                elif isinstance(variants, str):
                    ab_rows.append({
                        'Content Type': content_type.replace('_', ' ').title(),
                        'Variant': 'Base',
                        'Text': variants,
                    })
            if ab_rows:
                ab_df = pd.DataFrame(ab_rows)
                ab_df.to_excel(writer, sheet_name='A_B_Variants', index=False)

            caption_rows = []
            image_rows = []
            for content_type, platforms in campaign.get('images', {}).items():
                for platform, image_data in platforms.items():
                    image_rows.append({
                        'Content Type': content_type.replace('_', ' ').title(),
                        'Platform': platform,
                        'Image Present': bool(image_data),
                        'Caption': campaign.get('captions', {}).get(content_type, {}).get(platform, ''),
                    })
                    caption = campaign.get('captions', {}).get(content_type, {}).get(platform)
                    if caption is not None:
                        caption_rows.append({
                            'Content Type': content_type.replace('_', ' ').title(),
                            'Platform': platform,
                            'Caption': caption,
                        })
            if caption_rows:
                caption_df = pd.DataFrame(caption_rows)
                caption_df.to_excel(writer, sheet_name='Image Captions', index=False)
            if image_rows:
                image_df = pd.DataFrame(image_rows)
                image_df.to_excel(writer, sheet_name='Images', index=False)

            workbook = writer.book
            wrap_format = workbook.add_format({'text_wrap': True, 'valign': 'top'})
            for sheet_name in writer.sheets:
                worksheet = writer.sheets[sheet_name]
                worksheet.set_column('A:A', 25, wrap_format)
                worksheet.set_column('B:B', 25, wrap_format)
                worksheet.set_column('C:C', 80, wrap_format)
                worksheet.set_column('D:D', 40, wrap_format)
                worksheet.set_column('E:E', 20, wrap_format)

            if image_rows and 'Images' in writer.sheets:
                worksheet = writer.sheets['Images']
                row_index = 1
                for image_row in image_rows:
                    image_data = campaign.get('images', {}).get(image_row['Content Type'].lower().replace(' ', '_'), {}).get(image_row['Platform'])
                    if image_data:
                        try:
                            image_io = BytesIO(image_data)
                            worksheet.set_row(row_index, 90)
                            worksheet.insert_image(row_index, 4, f"{image_row['Content Type']}_{image_row['Platform']}.png", {'image_data': image_io, 'x_scale': 0.2, 'y_scale': 0.2})
                        except Exception:
                            pass
                    row_index += 1

        buffer.seek(0)
        return buffer

    def collect_feedback(self, campaign_id, content_type, rating, comments=""):
        feedback = {
            'campaign_id': campaign_id,
            'content_type': content_type,
            'rating': rating,
            'comments': comments,
            'timestamp': datetime.now()
        }
        st.session_state.feedback_data.append(feedback)
        return feedback

    def save_as_template(self, campaign, template_name, template_desc):
        new_template = {
            'name': template_name,
            'description': template_desc,
            'content_types': list(campaign.get('content', {}).keys()),
            'platforms': campaign.get('selected_platforms', []),
            'tone': campaign.get('tone', 'Professional'),
            'duration_days': 7,
            'category': 'Custom'
        }
        if 'saved_templates' not in st.session_state:
            st.session_state.saved_templates = []
        st.session_state.saved_templates.append(new_template)
        return new_template

    def load_campaigns_from_excel(self):
        """Load all campaigns from the Excel database."""
        if not os.path.exists(CAMPAIGN_DATABASE):
            return []
        try:
            campaigns = []
            xls = pd.ExcelFile(CAMPAIGN_DATABASE)
            if 'Campaigns' in xls.sheet_names:
                df = pd.read_excel(xls, sheet_name='Campaigns')
                for _, row in df.iterrows():
                    campaign_id = row['ID']
                    # Load detailed campaign data from other sheets if needed
                    campaign = self._load_campaign_details(xls, campaign_id)
                    if campaign:
                        campaigns.append(campaign)
            return campaigns
        except Exception as e:
            st.error(f"Error loading campaigns from database: {e}")
            return []

    def _load_campaign_details(self, xls, campaign_id):
        """Load detailed campaign data for a specific campaign ID."""
        # This is a simplified version; in a real implementation, you'd store more structured data
        # For now, return a placeholder or load from session state if available
        # Since we can't fully reconstruct from Excel, perhaps store JSON strings
        if 'CampaignDetails' in xls.sheet_names:
            df = pd.read_excel(xls, sheet_name='CampaignDetails')
            campaign_row = df[df['ID'] == campaign_id]
            if not campaign_row.empty:
                # Assuming we store a JSON string in a column
                import json
                data_str = str(campaign_row.iloc[0]['Data'])
                try:
                    campaign_data = json.loads(data_str)
                    # Convert string dates back to datetime objects
                    self._convert_dates_in_campaign(campaign_data)
                    return campaign_data
                except json.JSONDecodeError as e:
                    # Handle truncated JSON data due to Excel cell limit (32,767 chars)
                    # Silently attempt to reconstruct from overview data

                    # Try to load basic info from Campaigns sheet
                    if 'Campaigns' in xls.sheet_names:
                        campaigns_df = pd.read_excel(xls, sheet_name='Campaigns')
                        overview_row = campaigns_df[campaigns_df['ID'] == campaign_id]
                        if not overview_row.empty:
                            row = overview_row.iloc[0]
                            # Create a basic campaign structure
                            return {
                                'id': campaign_id,
                                'brand_info': {'brand_name': row.get('Brand', 'Unknown')},
                                'created_at': pd.to_datetime(row.get('Created', datetime.now())),
                                'selected_platforms': row.get('Platforms', '').split(', ') if row.get('Platforms') else [],
                                'content': {},  # Will be empty due to data loss
                                'platform_content': {},
                                'tone': row.get('Tone', ''),
                                'language': row.get('Language', ''),
                                'sentiment': row.get('Sentiment', ''),
                                'target_audience': row.get('Target Audience', ''),
                                'corrupted': True  # Mark as corrupted
                            }
                    return None
        return None

    def _convert_dates_in_campaign(self, campaign):
        """Convert string date fields back to datetime objects in a campaign."""
        if 'created_at' in campaign and isinstance(campaign['created_at'], str):
            try:
                campaign['created_at'] = pd.to_datetime(campaign['created_at'])
            except:
                campaign['created_at'] = datetime.now()
        
        # Convert dates in platform_content
        if 'platform_content' in campaign:
            for content_type, platforms in campaign['platform_content'].items():
                if isinstance(platforms, dict):
                    for platform, content in platforms.items():
                        if isinstance(content, dict):
                            if 'scheduled_time' in content and isinstance(content['scheduled_time'], str):
                                try:
                                    content['scheduled_time'] = pd.to_datetime(content['scheduled_time'])
                                except:
                                    pass
                            if 'posts' in content and isinstance(content['posts'], list):
                                for post in content['posts']:
                                    if isinstance(post, dict) and 'scheduled_time' in post and isinstance(post['scheduled_time'], str):
                                        try:
                                            post['scheduled_time'] = pd.to_datetime(post['scheduled_time'])
                                        except:
                                            pass

    def _clean_campaign_for_storage(self, campaign):
        """Clean campaign data to avoid Excel cell size limits by removing large image data."""
        # Create a copy to avoid modifying the original
        cleaned = campaign.copy()

        # Remove large image data from brand_info
        if 'brand_info' in cleaned and 'images' in cleaned['brand_info']:
            cleaned_images = []
            for img in cleaned['brand_info']['images']:
                if isinstance(img, dict):
                    # Keep only metadata, remove large base64 data
                    cleaned_img = {k: v for k, v in img.items() if k != 'data'}
                    # If data exists and is very large, replace with placeholder
                    if 'data' in img and len(str(img.get('data', ''))) > 1000:
                        cleaned_img['data'] = '[LARGE_IMAGE_DATA_REMOVED]'
                    else:
                        cleaned_img['data'] = img.get('data')
                    cleaned_images.append(cleaned_img)
                else:
                    cleaned_images.append(img)
            cleaned['brand_info']['images'] = cleaned_images

        # Remove large image data from platform_content
        if 'platform_content' in cleaned:
            for content_type, platforms in cleaned['platform_content'].items():
                if isinstance(platforms, dict):
                    for platform, content in platforms.items():
                        if isinstance(content, dict) and 'images' in content:
                            cleaned_images = []
                            for img in content['images']:
                                if isinstance(img, dict):
                                    cleaned_img = {k: v for k, v in img.items() if k != 'data'}
                                    if 'data' in img and len(str(img.get('data', ''))) > 1000:
                                        cleaned_img['data'] = '[LARGE_IMAGE_DATA_REMOVED]'
                                    else:
                                        cleaned_img['data'] = img.get('data')
                                    cleaned_images.append(cleaned_img)
                                else:
                                    cleaned_images.append(img)
                            content['images'] = cleaned_images

        return cleaned

    def save_campaigns_to_excel(self, campaigns):
        """Save all campaigns to the Excel database."""
        try:
            # Ensure all campaigns have proper datetime objects before saving
            for campaign in campaigns:
                self._convert_dates_in_campaign(campaign)
            
            with pd.ExcelWriter(CAMPAIGN_DATABASE, engine='xlsxwriter') as writer:
                # Campaigns overview sheet
                campaign_rows = []
                detail_rows = []
                for campaign in campaigns:
                    campaign_rows.append({
                        'ID': campaign['id'],
                        'Brand': campaign['brand_info'].get('brand_name', ''),
                        'Created': campaign['created_at'].strftime('%Y-%m-%d %H:%M'),
                        'Platforms': ', '.join(campaign.get('selected_platforms', [])),
                        'Content Types': ', '.join(campaign.get('content', {}).keys()),
                        'Tone': campaign.get('tone', ''),
                        'Language': campaign.get('language', ''),
                        'Sentiment': campaign.get('sentiment', ''),
                        'Target Audience': campaign.get('target_audience', ''),
                    })
                    # Store full campaign data as JSON for detailed loading
                    # Clean the campaign data to avoid Excel cell size limits
                    campaign_copy = self._clean_campaign_for_storage(campaign.copy())
                    import json
                    detail_rows.append({
                        'ID': campaign['id'],
                        'Data': json.dumps(campaign_copy, default=str),
                    })

                if campaign_rows:
                    campaigns_df = pd.DataFrame(campaign_rows)
                    campaigns_df.to_excel(writer, sheet_name='Campaigns', index=False)

                if detail_rows:
                    details_df = pd.DataFrame(detail_rows)
                    details_df.to_excel(writer, sheet_name='CampaignDetails', index=False)

                # Format the workbook
                workbook = writer.book
                wrap_format = workbook.add_format({'text_wrap': True, 'valign': 'top'})
                for sheet_name in writer.sheets:
                    worksheet = writer.sheets[sheet_name]
                    worksheet.set_column('A:A', 15, wrap_format)
                    worksheet.set_column('B:B', 25, wrap_format)
                    worksheet.set_column('C:C', 20, wrap_format)
                    worksheet.set_column('D:D', 30, wrap_format)
                    worksheet.set_column('E:E', 30, wrap_format)
                    worksheet.set_column('F:F', 15, wrap_format)
                    worksheet.set_column('G:G', 15, wrap_format)
                    worksheet.set_column('H:H', 15, wrap_format)
                    worksheet.set_column('I:I', 15, wrap_format)

        except Exception as e:
            st.error(f"Error saving campaigns to database: {e}")


# =========================
# Main App
# =========================
def main():
    st.set_page_config(
        page_title="AI Campaign Generator Pro",
        page_icon="🚀",
        layout="wide"
    )

    # Session state initialization
    if 'campaigns' not in st.session_state:
        st.session_state.campaigns = []
    if 'competitor_data' not in st.session_state:
        st.session_state.competitor_data = {}
    if 'analytics_data' not in st.session_state:
        st.session_state.analytics_data = {}
    if 'scheduled_posts' not in st.session_state:
        st.session_state.scheduled_posts = []
    if 'feedback_data' not in st.session_state:
        st.session_state.feedback_data = []
    if 'saved_templates' not in st.session_state:
        st.session_state.saved_templates = []
    if 'brand_profile' not in st.session_state:
        st.session_state.brand_profile = None
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    if 'brand_style_guide' not in st.session_state:
        st.session_state.brand_style_guide = None
    if 'show_style_guide' not in st.session_state:
        st.session_state.show_style_guide = False

    # Load campaigns from database
    generator = SmartAICampaignGenerator()
    if not st.session_state.campaigns:
        st.session_state.campaigns = generator.load_campaigns_from_excel()
    
    # Ensure all campaigns have proper datetime objects
    for c in st.session_state.campaigns:
        generator._convert_dates_in_campaign(c)
    st.markdown("""
    <style>
    .stButton>button {
        background-color: #2E86AB;
        color: white;
        border-radius: 5px;
        padding: 0.5rem 1rem;
        font-weight: bold;
    }
    .stButton>button:hover {
        background-color: #1e5a7a;
    }
    .chat-message {
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    .user-message {
        background-color: #e3f2fd;
    }
    .assistant-message {
        background-color: #f5f5f5;
    }
    </style>
    """, unsafe_allow_html=True)

    st.title("🚀 AI Campaign Generator Pro")
    st.markdown("*Create comprehensive marketing campaigns with AI-powered content*")

    # Sidebar
    with st.sidebar:
        st.header("Campaign Settings")

        st.link_button(
            label="🎥 Generate Video Campaign",
            url="http://localhost:8501",
            use_container_width=True
        )
        st.divider()

        with st.expander("🤖 AI Assistant", expanded=False):
            st.markdown("**Ask me anything about your campaign!**")
            user_question = st.text_input("Your question:", key="chat_input", placeholder="How do I improve engagement?")
            if st.button("Ask Assistant", key="ask_btn"):
                if user_question:
                    with st.spinner("Thinking..."):
                        response = generator.ai_chat_assistant(user_question, context=True)
                        st.session_state.chat_history.append({'role': 'user', 'message': user_question})
                        st.session_state.chat_history.append({'role': 'assistant', 'message': response})
                        st.success("✅ Answer:")
                        st.write(response)
            if st.session_state.chat_history:
                st.markdown("**Recent Chat:**")
                for msg in st.session_state.chat_history[-3:]:
                    if msg['role'] == 'user':
                        st.markdown(f"**You:** {msg['message'][:100]}...")
                    else:
                        st.markdown(f"**Assistant:** {msg['message'][:100]}...")

        st.subheader("1. Brand Information")
        input_method = st.radio("Choose input method:", ["Enter Manually", "Extract from Website"])

        if input_method == "Extract from Website":
            website_url = st.text_input("Website URL:", placeholder="https://example.com")

            col1, col2 = st.columns(2)
            with col1:
                if st.button("Extract Info"):
                    with st.spinner("Extracting..."):
                        brand_data = generator.extract_website_info(website_url)
                        if brand_data:
                            st.session_state.brand_profile = brand_data
                            st.success("✅ Extracted!")
                            with st.spinner("Generating style guide..."):
                                generator.generate_brand_style_guide(brand_data, website_url)
                                st.success("✅ Style guide created!")

            with col2:
                if st.button("View Style Guide"):
                    if st.session_state.brand_style_guide:
                        st.session_state.show_style_guide = True
                        st.rerun()

        if 'brand_profile' in st.session_state and st.session_state.brand_profile:
            brand_info = st.session_state.brand_profile
            st.write("**Extracted Info:**")
            st.write(f"**Name:** {brand_info.get('brand_name', 'N/A')}")
            st.write(f"**Description:** {brand_info.get('description', 'N/A')[:100]}...")
        else:
            brand_name = st.text_input("Brand Name:", placeholder="Your brand name")
            brand_description = st.text_area("Brand Description:", placeholder="Describe your brand")
            industry = st.text_input("Industry:", placeholder="e.g., Technology")

            if brand_name and brand_description:
                st.session_state.brand_profile = {
                    'brand_name': brand_name,
                    'description': brand_description,
                    'industry': industry,
                    'keywords': brand_description.split()[:10]
                }

        st.subheader("2. Campaign Configuration")

        use_template = st.checkbox("📚 Use Template")
        if use_template:
            templates = generator.get_all_templates()
            if templates:
                template_list = list(templates.values())
                template_names = [f"{t.get('name', k)} ({t.get('category', 'General')})" for k, t in templates.items()]
                selected_template_name = st.selectbox("Choose Template:", template_names)
                selected_idx = template_names.index(selected_template_name)
                selected_template = template_list[selected_idx]
                st.info(f"**Description:** {selected_template.get('description', '')}")
                st.write(f"**Platforms:** {', '.join(selected_template.get('platforms', []))}")
                st.write(f"**Content Types:** {', '.join(selected_template.get('content_types', []))}")
                if st.button("Load Template"):
                    st.session_state.template_loaded = selected_template
                    st.success("✅ Template loaded! Settings applied below.")

        template_defaults = st.session_state.get('template_loaded', {})

        content_types = st.multiselect(
            "Content Types:",
            ["social_media_posts", "ad_copy", "email_campaigns", "blog_content"],
            default=template_defaults.get('content_types', ["social_media_posts"])
        )

        selected_platforms = st.multiselect(
            "Target Platforms:",
            list(PLATFORM_SPECS.keys()),
            default=template_defaults.get('platforms', ["Instagram", "Facebook"])
        )

    tone_options = ["Professional", "Casual", "Friendly", "Authoritative"]
    template_tone = template_defaults.get('tone', 'Professional')
    tone_index = tone_options.index(template_tone) if template_tone in tone_options else 0
    tone = st.selectbox("Tone:", tone_options, index=tone_index)
    language = st.selectbox("Language:", list(LANGUAGES.keys()), index=0)
    sentiment = st.selectbox("Sentiment:", ["Positive", "Neutral", "Excited"])
    target_audience = st.selectbox("Target Audience:", ["General", "Young Adults", "Professionals"])

    st.markdown("**Generation Options:**")
    generate_images = st.checkbox("Generate AI Images", value=True)
    generate_ab_variants = st.checkbox("Generate A/B Variants", value=True)
    generate_captions = st.checkbox("Generate Captions", value=True)

    st.subheader("3. Competitor Analysis")
    enable_competitor = st.checkbox("Enable competitor analysis")
    competitor_urls = []
    if enable_competitor:
        for i in range(3):
            url = st.text_input(f"Competitor {i+1} URL:", key=f"comp_{i}")
            if url:
                competitor_urls.append(url)

    st.subheader("4. Generate Campaign")
    can_generate = bool(st.session_state.brand_profile and selected_platforms and content_types)

    if not can_generate:
        st.error("❌ Please complete brand info and select platforms")

    if st.button("🚀 Generate Campaign", type="primary", disabled=not can_generate):
        if can_generate:
            try:
                if enable_competitor and competitor_urls:
                    with st.spinner("Analyzing competitors..."):
                        generator.analyze_competitors(
                            st.session_state.brand_profile.get('brand_name', ''),
                            st.session_state.brand_profile.get('industry', ''),
                            competitor_urls
                        )

                options = {
                    'generate_images': generate_images,
                    'generate_ab_variants': generate_ab_variants,
                    'generate_captions': generate_captions
                }

                st.info(f"[DEBUG] Generating campaign with: brand={st.session_state.brand_profile}, content_types={content_types}, platforms={selected_platforms}, tone={tone}, lang={language}, sentiment={sentiment}, audience={target_audience}, options={options}")

                campaign = generator.create_campaign_package(
                    st.session_state.brand_profile,
                    content_types,
                    selected_platforms,
                    tone,
                    language,
                    sentiment,
                    target_audience,
                    options
                )

                st.success("🎉 Campaign generated!")
                st.session_state.current_campaign = campaign
                # Save to database
                generator.save_campaigns_to_excel(st.session_state.campaigns)
            except Exception as e:
                st.error(f"❌ Error during campaign generation: {e}")
                st.exception(e)

    # Main content area
    if st.session_state.get('show_style_guide'):
        st.header("🎨 Brand Style Guide")

        if st.session_state.brand_style_guide:
            style_guide = st.session_state.brand_style_guide

            tab1, tab2, tab3, tab4 = st.tabs(["🎨 Colors", "✍️ Typography", "📢 Voice & Tone", "🖼️ Design Principles"])

            with tab1:
                st.subheader("Color Palette")
                colors_data = style_guide.get('colors', {})
                cols = st.columns(5)
                for i, (color_name, color_value) in enumerate(list(colors_data.items())[:5]):
                    if isinstance(color_value, str) and color_value.startswith('#'):
                        with cols[i]:
                            st.markdown(f"""
                            <div style="background-color: {color_value}; padding: 40px; border-radius: 10px; text-align: center; margin-bottom: 10px;">
                                <span style="color: white; font-weight: bold; text-shadow: 1px 1px 2px black;">{color_name.title()}</span>
                            </div>
                            <p style="text-align: center; font-family: monospace;">{color_value}</p>
                            """, unsafe_allow_html=True)

            with tab2:
                st.subheader("Typography System")
                typography = style_guide.get('typography', [])
                primary_font = typography[0] if len(typography) > 0 else 'Sans-serif'
                secondary_font = typography[1] if len(typography) > 1 else 'Serif'
                st.markdown(f"**Primary Font:** `{primary_font}`")
                st.markdown(f"**Secondary Font:** `{secondary_font}`")
                st.markdown(f"**Body Size:** 16px")
                st.markdown(f"**Line Height:** 1.6")
                st.markdown("**Heading Sizes:**")
                heading_sizes = {'H1': '32px', 'H2': '24px', 'H3': '18.72px'}
                for heading, size in heading_sizes.items():
                    st.markdown(f"- **{heading.upper()}:** {size}")

            with tab3:
                st.subheader("Brand Voice & Tone")
                voice = style_guide.get('voice_tone', '')
                st.markdown(f"**Overall Tone:** {voice if voice else 'Professional'}")

            with tab4:
                st.subheader("Design Principles")
                principles = style_guide.get('design_principles', [])
                for principle in principles:
                    st.markdown(f"- {principle}")

            if st.button("← Back to Campaign"):
                st.session_state.show_style_guide = False
                st.rerun()

        else:
            st.info("No style guide available. Extract brand info from a website first!")

    elif 'current_campaign' not in st.session_state:
        pass

    else:
        # Campaign view with all tabs
        campaign = st.session_state.current_campaign

        # Top action bar
        action_cols = st.columns([3, 1, 1, 1])
        with action_cols[0]:
            st.markdown(f"**Campaign:** {campaign['brand_info'].get('brand_name', 'N/A')} | **ID:** {campaign['id']}")
        with action_cols[1]:
            if st.button("💾 Save as Template"):
                st.session_state.show_save_template = True
        with action_cols[2]:
            if st.button("🎨 View Style Guide"):
                st.session_state.show_style_guide = True
                st.rerun()
        with action_cols[3]:
            if st.button("🔄 New Campaign"):
                del st.session_state.current_campaign
                st.rerun()

        # Save as template modal
        if st.session_state.get('show_save_template'):
            with st.expander("💾 Save as Template", expanded=True):
                template_name = st.text_input("Template Name:", placeholder="My Awesome Template")
                template_desc = st.text_area("Description:", placeholder="Describe this template...")

                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Save Template"):
                        if template_name:
                            generator.save_as_template(campaign, template_name, template_desc)
                            st.success(f"✅ Template '{template_name}' saved!")
                            st.session_state.show_save_template = False
                        else:
                            st.error("Please enter a template name")
                with col2:
                    if st.button("Cancel"):
                        st.session_state.show_save_template = False
                        st.rerun()

        tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10 = st.tabs([
            "📝 Content", "🎨 Images", "🧪 A/B Testing", "📅 Calendar",
            "📊 Analytics", "🏆 Competitors", "💾 Export", "🔄 Feedback", "🤖 AI Chat", "📚 Brand Memory"
        ])

        with tab1:
            st.header("Generated Content")
            selected_platforms = campaign.get('selected_platforms', [])
            st.info(f"📱 Platforms: {', '.join(selected_platforms)}")
            for content_type in campaign['content']:
                st.subheader(f"📄 {content_type.replace('_', ' ').title()}")

                st.markdown("**Base Content:**")
                st.write(campaign['content'][content_type])

                if content_type in campaign.get('platform_content', {}):
                    st.markdown("**Platform Versions:**")
                    platforms = list(campaign['platform_content'][content_type].keys())

                    if len(platforms) <= 3:
                        cols = st.columns(len(platforms))
                        for i, platform in enumerate(platforms):
                            with cols[i]:
                                st.markdown(f"**{platform}**")
                                content = campaign['platform_content'][content_type][platform]
                                st.text_area(
                                    f"{platform} Content",
                                    value=content,
                                    height=200,
                                    key=f"content_{content_type}_{platform}",
                                    disabled=True
                                )

                                if st.button(f"📋 Copy", key=f"copy_{content_type}_{platform}"):
                                    st.code(content)
                                    st.success("Displayed above!")

                                col1, col2 = st.columns(2)
                                with col1:
                                    st.caption(f"📝 {len(content)} chars")
                                with col2:
                                    st.caption(f"🔗 {content.count('#')} hashtags")
                    else:
                        platform_tabs = st.tabs(platforms)
                        for i, platform in enumerate(platforms):
                            with platform_tabs[i]:
                                content = campaign['platform_content'][content_type][platform]
                                st.write(content)
                                cols = st.columns(3)
                                with cols[0]:
                                    st.metric("Characters", len(content))
                                with cols[1]:
                                    st.metric("Hashtags", content.count('#'))
                                with cols[2]:
                                    st.metric("Words", len(content.split()))
                st.divider()

        with tab2:
            st.header("Generated Images")

            # Website images
            if campaign['brand_info'].get('images'):
                with st.expander("📸 Website Images", expanded=False):
                    st.info(f"Found {len(campaign['brand_info']['images'])} images from website")
                    imgs = campaign['brand_info']['images']
                    cols = st.columns(min(3, len(imgs)))
                    for idx, img in enumerate(imgs[:9]):
                        with cols[idx % 3]:
                            try:
                                st.image(img['url'], caption=f"{img['type']}: {img['alt'][:30]}...", width=300)
                            except:
                                st.caption(f"❌ Could not load: {img['alt'][:30]}")
            # AI generated images (server-side)
            st.subheader("🎨 AI Generated Images (Server)")
            for content_type in campaign.get('images', {}):
                st.markdown(f"### {content_type.replace('_', ' ').title()}")
                platforms = list(campaign['images'][content_type].keys())
                if platforms:
                    image_tabs = st.tabs(platforms)
                    for i, platform in enumerate(platforms):
                        with image_tabs[i]:
                            st.markdown(f"**{platform} Image ({PLATFORM_SPECS[platform]['image_ratio']})**")
                            image_data = campaign['images'][content_type][platform]
                            if image_data:
                                cols = st.columns([1, 1])
                                with cols[0]:
                                    st.image(image_data, width=360)
                                    st.download_button(
                                        f"📥 Download Image",
                                        data=image_data,
                                        file_name=f"{platform}_{content_type}.png",
                                        mime="image/png",
                                        key=f"dl_img_{content_type}_{platform}"
                                    )
                                with cols[1]:
                                    if content_type in campaign.get('captions', {}) and platform in campaign['captions'][content_type]:
                                        st.markdown("**Suggested Caption:**")
                                        caption = campaign['captions'][content_type][platform]
                                        st.text_area("Suggested Caption", value=caption, height=200, key=f"cap_{content_type}_{platform}", disabled=True, label_visibility="collapsed")
                                        st.download_button(
                                            "📥 Download Caption",
                                            data=caption,
                                            file_name=f"{platform}_{content_type}_caption.txt",
                                            key=f"dl_cap_{content_type}_{platform}"
                                        )
                            else:
                                st.error("Image generation failed")
                st.divider()

            # Optional client-side HTML UI
            with st.expander("🧪 Try the client-side HF Web UI (uses your HF token in browser)"):
                html_code = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>AI Text to Image Generator</title>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.2/css/all.min.css" />
  <style>
    body {
      background-color: #111;
      font-family: Arial, Helvetica, sans-serif;
      display: flex;
      flex-direction: column;
      align-items: center;
      padding-top: 20px;
      color: #fff;
      margin: 0;
    }
    .search-box {
      width: 500px;
      max-width: 90%;
      display: flex;
      align-items: center;
      background-color: #1e1e1e;
      border: 1px solid #2a2a2a;
      border-radius: 10px;
      padding: 10px;
    }
    .search-box input {
      flex: 1;
      background: none;
      outline: none;
      border: none;
      padding: 8px 12px;
      border-radius: 15px;
      color: #fff;
      font-size: 1rem;
    }
    .search-box button {
      background-color: #00bcd4;
      border: none;
      color: #fff;
      padding: 8px 12px;
      border-radius: 10px;
      cursor: pointer;
      font-size: 1rem;
      transition: 0.2s;
    }
    .search-box button:hover {
      background-color: #00acc1;
    }
    .result-container {
      margin-top: 20px;
      text-align: center;
      width: 500px;
      max-width: 90%;
    }
    .image-wrapper {
      position: relative;
      display: inline-block;
    }
    img {
      max-width: 100%;
      border-radius: 15px;
    }
    .icon-btns {
      position: absolute;
      top: 8px;
      right: 8px;
      display: flex;
      gap: 6px;
    }
    .icon-btns button {
      background-color: rgba(0, 0, 0, 0.6);
      color: #fff;
      padding: 6px;
      border: none;
      cursor: pointer;
      border-radius: 50%;
      font-size: 0.9rem;
      transition: 0.2s;
    }
    .icon-btns button:hover {
      background-color: rgba(0, 0, 0, 0.8);
    }
    .loading-text {
      font-size: 1rem;
      color: #aaa;
      margin-top: 20px;
      animation: blink 1s infinite;
    }
    @keyframes blink { 50% { opacity: 0.6; } }
  </style>
</head>
<body>
  <h3>AI Image Generator (Hugging Face)</h3>
  <div class="search-box">
    <input type="text" id="prompt" placeholder="Type your image description..." />
    <button onclick="generateImage()"><i class="fa-solid fa-arrow-right"></i></button>
  </div>
  <div class="result-container" id="result"></div>

  <script>
    const HF_TOKEN = "HF_TOKEN_PLACEHOLDER";

    async function generateImage() {
      const prompt = document.getElementById("prompt").value.trim();
      if (!prompt) { alert("Please enter a prompt."); return; }

      document.getElementById("result").innerHTML =
        '<div class="loading-text">🚀 Generating ultra-realistic image... please wait...</div>';

      try {
        const response = await fetch(
          "https://router.huggingface.co/hf-inference/models/black-forest-labs/FLUX.1-schnell",
          {
            method: "POST",
            headers: {
              Authorization: "Bearer " + HF_TOKEN,
              "Content-Type": "application/json",
            },
            body: JSON.stringify({
              inputs: prompt,
              parameters: {
                negative_prompt:
                  "blurry, cartoon, fake, cgi, painting, illustration, extra wheels, distorted, watermark, text, low detail, unrealistic",
                num_inference_steps: 50,
                guidance_scale: 9,
                width: 768,
                height: 768
              },
            }),
          }
        );

        if (!response.ok) throw new Error("Image generation failed. Please try again.");

        const blob = await response.blob();
        const imgURL = URL.createObjectURL(blob);

        document.getElementById("result").innerHTML = `
          <div class="image-wrapper" id="imageContainer">
            <div class="icon-btns">
              <button onclick="downloadImage('${imgURL}')"><i class="fa-solid fa-download"></i></button>
              <button onclick="deleteImage()"><i class="fa-solid fa-trash"></i></button>
            </div>
            <img id="generatedImage" src="${imgURL}" style="border-radius:12px;max-width:100%;box-shadow:0 0 20px rgba(0,0,0,0.2);" />
          </div>
        `;
      } catch (error) {
        document.getElementById("result").innerHTML =
          '<div class="loading-text" style="color:red;">' + error.message + '</div>';
      }
    }

    function downloadImage(url) {
      const a = document.createElement("a");
      a.href = url;
      a.download = "ai-generated-image.png";
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    }

    function deleteImage() {
      document.getElementById("result").innerHTML = "";
    }
  </script>
</body>
</html>
"""
                token = generator.hf_api_key or ""
                components.html(html_code.replace("HF_TOKEN_PLACEHOLDER", token), height=780, scrolling=True)

        with tab3:
            st.header("A/B Testing")
            for content_type in campaign.get('ab_variants', {}):
                st.subheader(f"🧪 {content_type.replace('_', ' ').title()}")
                st.markdown("**Test Variants:**")
                st.write(campaign['ab_variants'][content_type])

                col1, col2 = st.columns([2, 1])
                with col1:
                    if st.button(f"📊 Generate Test Results", key=f"ab_{content_type}"):
                        results = generator.generate_ab_test_results(campaign['id'], content_type)
                        st.markdown("**Results:**")
                        df = pd.DataFrame(results['results']).T
                        st.dataframe(df, use_container_width=True)
                        st.success(f"🏆 Winner: {results['winner']} (Confidence: {results['confidence']}%)")
                        fig = px.bar(
                            x=list(results['results'].keys()),
                            y=[r['engagement_rate'] for r in results['results'].values()],
                            title="Engagement Rate Comparison",
                            labels={'x': 'Variant', 'y': 'Engagement Rate (%)'}
                        )
                        st.plotly_chart(fig, use_container_width=True)
                with col2:
                    st.markdown("**Testing Tips:**")
                    st.info("""
                    - Run tests for 7+ days
                    - Test one element at a time
                    - Ensure sufficient sample size
                    - Monitor significance levels
                    """)
                st.divider()

        with tab4:
            st.header("📅 Content Calendar")
            st.markdown("**Visual Calendar with Scheduling**")

            col1, col2, col3 = st.columns([1, 2, 1])
            with col1:
                selected_year = st.selectbox("Year:", range(datetime.now().year, datetime.now().year + 2), key="cal_year")
            with col2:
                selected_month = st.selectbox("Month:", range(1, 13),
                                              index=datetime.now().month - 1,
                                              format_func=lambda x: cal_module.month_name[x],
                                              key="cal_month")
            with col3:
                if st.button("📅 Today"):
                    st.rerun()

            cal = cal_module.monthcalendar(selected_year, selected_month)
            st.markdown("---")

            weekdays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
            header_cols = st.columns(7)
            for i, day in enumerate(weekdays):
                with header_cols[i]:
                    st.markdown(f"**{day}**")

            for week in cal:
                week_cols = st.columns(7)
                for i, day in enumerate(week):
                    with week_cols[i]:
                        if day == 0:
                            st.markdown("")
                        else:
                            current_date = datetime(selected_year, selected_month, day).date()
                            posts_on_day = [p for p in st.session_state.scheduled_posts
                                            if p['scheduled_time'].date() == current_date]

                            if posts_on_day:
                                st.markdown(f"""
                                <div style="border: 2px solid #2E86AB; border-radius: 5px; padding: 10px; background-color: #e3f2fd;">
                                    <strong>{day}</strong><br>
                                    <small>📌 {len(posts_on_day)} post(s)</small>
                                </div>
                                """, unsafe_allow_html=True)
                            else:
                                st.markdown(f"""
                                <div style="border: 1px solid #ddd; border-radius: 5px; padding: 10px;">
                                    <strong>{day}</strong>
                                </div>
                                """, unsafe_allow_html=True)

            st.markdown("---")

            st.subheader("📝 Schedule New Post")
            if 'campaign' not in locals():
                campaign = st.session_state.get('current_campaign', {'id': None, 'content': {}, 'selected_platforms': []})
            sched_cols = st.columns([2, 2, 2, 2, 2])
            with sched_cols[0]:
                content_type = st.selectbox("Content:", list(campaign.get('content', {}).keys()), key="sched_content")
            with sched_cols[1]:
                platform = st.selectbox("Platform:", campaign.get('selected_platforms', []), key="sched_platform")
            with sched_cols[2]:
                date = st.date_input("Date:", min_value=datetime.now().date(), key="sched_date")
            with sched_cols[3]:
                time_val = st.time_input("Time:", key="sched_time")
            with sched_cols[4]:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("📅 Schedule Post", key="sched_btn"):
                    scheduled = datetime.combine(date, time_val)
                    post = generator.schedule_post(campaign.get('id'), content_type, platform, scheduled)
                    st.success(f"✅ Scheduled for {scheduled.strftime('%Y-%m-%d %H:%M')}")
                    st.rerun()

            st.subheader("📋 Scheduled Posts")
            if 'campaign' not in locals():
                campaign = {'id': None, 'content': {}, 'selected_platforms': []}
            if 'campaign' not in locals():
                campaign = st.session_state.get('current_campaign', {'id': None})
            posts = [p for p in st.session_state.scheduled_posts if p.get('campaign_id') == campaign.get('id')]
            posts.sort(key=lambda x: x['scheduled_time'])

            if posts:
                for post in posts:
                    cols = st.columns([3, 2, 2, 1])
                    with cols[0]:
                        st.write(f"**{post['content_type'].replace('_', ' ').title()}**")
                    with cols[1]:
                        st.write(f"📱 {post['platform']}")
                    with cols[2]:
                        st.write(f"📅 {post['scheduled_time'].strftime('%Y-%m-%d %H:%M')}")
                    with cols[3]:
                        if st.button("🗑️", key=f"del_{post['id']}"):
                            if 'post' not in locals():
                                post = {'id': None}
                            st.session_state.scheduled_posts = [p for p in st.session_state.scheduled_posts if p.get('id') != post.get('id')]
                            st.rerun()
                    st.divider()
            else:
                st.info("No posts scheduled yet. Use the form above to schedule content!")

        with tab5:
            st.header("📊 Performance Analytics")
            st.info(f"Analytics for: {', '.join(campaign['selected_platforms'])}")

            if st.button("📊 Generate Performance Report"):
                with st.spinner("Generating metrics..."):
                    for ct in campaign['content']:
                        for platform in campaign['selected_platforms']:
                            generator.simulate_performance_metrics(campaign['id'], ct, platform)
                    st.success("✅ Report generated!")

            if campaign['id'] in st.session_state.analytics_data:
                analytics = st.session_state.analytics_data[campaign['id']]

                if analytics.get('performance'):
                    total_views = 0
                    total_clicks = 0
                    total_likes = 0
                    total_shares = 0

                    for ct, platforms in analytics['performance'].items():
                        if isinstance(platforms, dict):
                            for platform, metrics in platforms.items():
                                if isinstance(metrics, dict):
                                    total_views += metrics.get('views', 0)
                                    total_clicks += metrics.get('clicks', 0)
                                    total_likes += metrics.get('likes', 0)
                                    total_shares += metrics.get('shares', 0)

                    metric_cols = st.columns(4)
                    with metric_cols[0]:
                        st.metric("👁️ Total Views", f"{total_views:,}")
                    with metric_cols[1]:
                        st.metric("🖱️ Total Clicks", f"{total_clicks:,}")
                    with metric_cols[2]:
                        st.metric("❤️ Total Likes", f"{total_likes:,}")
                    with metric_cols[3]:
                        st.metric("🔄 Total Shares", f"{total_shares:,}")

                    ctr = (total_clicks / total_views * 100) if total_views > 0 else 0
                    engagement = ((total_likes + total_shares + total_clicks) / total_views * 100) if total_views > 0 else 0
                    st.markdown(f"**CTR:** {ctr:.2f}% | **Engagement Rate:** {engagement:.2f}%")

                    platform_data = []
                    for ct, platforms in analytics['performance'].items():
                        if isinstance(platforms, dict):
                            for platform, metrics in platforms.items():
                                if isinstance(metrics, dict):
                                    platform_data.append({
                                        'Content': ct,
                                        'Platform': platform,
                                        'Views': metrics.get('views', 0),
                                        'Clicks': metrics.get('clicks', 0),
                                        'Engagement Rate': metrics.get('engagement_rate', 0)
                                    })

                    if platform_data:
                        df = pd.DataFrame(platform_data)
                        st.dataframe(df, use_container_width=True)
                        fig_views = px.bar(df, x='Platform', y='Views', color='Content', title="Views by Platform")
                        st.plotly_chart(fig_views, use_container_width=True)
                        fig_engagement = px.line(df, x='Platform', y='Engagement Rate', color='Content', title="Engagement Rate by Platform", markers=True)
                        st.plotly_chart(fig_engagement, use_container_width=True)

        with tab6:
            st.header("🏆 Competitor Analysis")

            if 'competitor_data' in st.session_state and st.session_state.competitor_data:
                data = st.session_state.competitor_data

                st.info(f"📅 Analysis Date: {data['timestamp'].strftime('%Y-%m-%d %H:%M')}")

                st.subheader("📊 Analysis Report")
                st.write(data.get('analysis', 'No analysis available'))

                if data.get('competitor_websites'):
                    st.subheader("🌐 Competitor Websites Analyzed")

                    for url, info in data['competitor_websites'].items():
                        with st.expander(f"📊 {info.get('brand_name', url)}", expanded=False):
                            cols = st.columns([1, 2])

                            with cols[0]:
                                if info.get('images') and len(info['images']) > 0:
                                    try:
                                        st.image(info['images'][0]['url'], width=260)
                                    except:
                                        st.write("No image available")

                            with cols[1]:
                                st.write(f"**URL:** {url}")
                                st.write(f"**Description:** {info.get('description', 'N/A')[:200]}...")

                                if info.get('keywords'):
                                    st.write(f"**Keywords:** {', '.join(info['keywords'][:10])}")

                                if info.get('social_links'):
                                    st.write("**Social Presence:**")
                                    for platform, link in info['social_links'].items():
                                        st.write(f"- {platform.title()}: {link[:50]}...")
            else:
                st.info("💡 No competitor analysis available. Enable it in the sidebar and regenerate campaign.")

        with tab7:
            st.header("💾 Export Campaign")

            export_cols = st.columns(2)

            with export_cols[0]:
                st.subheader("📄 PDF Report")
                st.write("Export comprehensive campaign report")

                if st.button("Generate PDF Report", key="gen_pdf"):
                    with st.spinner("Creating PDF..."):
                        pdf = generator.export_campaign_to_pdf(campaign)
                        st.download_button(
                            "📥 Download PDF",
                            data=pdf.getvalue(),
                            file_name=f"campaign_{campaign['id']}.pdf",
                            mime="application/pdf"
                        )

            with export_cols[1]:
                st.subheader("📊 Excel Spreadsheet")
                st.write("Export campaign data to Excel")

                if st.button("Generate Excel Report", key="gen_excel"):
                    with st.spinner("Creating Excel..."):
                        excel = generator.export_campaign_to_excel(campaign)
                        st.download_button(
                            "📥 Download Excel",
                            data=excel.getvalue(),
                            file_name=f"campaign_{campaign['id']}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )

        with tab8:
            st.header("🔄 Feedback & Continuous Learning")
            st.write("Help us improve future content generation by providing feedback!")

            for content_type in campaign['content']:
                with st.expander(f"📝 {content_type.replace('_', ' ').title()}", expanded=False):
                    cols = st.columns([1, 2])

                    with cols[0]:
                        rating = st.slider(
                            "Quality Rating",
                            min_value=1,
                            max_value=5,
                            value=3,
                            key=f"rating_{content_type}",
                            help="Rate the quality of generated content"
                        )
                        st.write("⭐" * rating)

                    with cols[1]:
                        comments = st.text_area(
                            "Your Feedback",
                            placeholder="What did you like? What could be improved?",
                            key=f"comments_{content_type}",
                            height=100
                        )

                    if st.button(f"Submit Feedback", key=f"submit_{content_type}"):
                        generator.collect_feedback(campaign['id'], content_type, rating, comments)
                        st.success("✅ Thank you for your feedback! This helps improve our AI.")

            if st.session_state.feedback_data:
                st.markdown("---")
                st.subheader("📊 Feedback History")

                feedback_df = pd.DataFrame([
                    {
                        'Content Type': f['content_type'].replace('_', ' ').title(),
                        'Rating': '⭐' * f['rating'],
                        'Comments': f['comments'][:50] + "..." if len(f['comments']) > 50 else f['comments'],
                        'Date': f['timestamp'].strftime('%Y-%m-%d')
                    }
                    for f in st.session_state.feedback_data[-10:]
                ])

                st.dataframe(feedback_df, use_container_width=True)

                avg_rating = sum([f['rating'] for f in st.session_state.feedback_data]) / len(st.session_state.feedback_data)
                st.metric("Average Rating", f"{avg_rating:.1f} / 5.0")

        with tab9:
            st.header("🤖 AI Campaign Assistant")

            st.write("Ask questions about your campaign, get suggestions, or request content improvements!")

            chat_container = st.container()
            with chat_container:
                for msg in st.session_state.chat_history[-10:]:
                    if msg['role'] == 'user':
                        st.markdown(f"""
                        <div class="chat-message user-message" style="color:black;">
                            <strong style="color:black;">You:</strong> {msg['message']}
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                        <div class="chat-message assistant-message" style="color:black;">
                            <strong style="color:black;">🤖 Assistant:</strong> {msg['message']}
                        </div>
                        """, unsafe_allow_html=True)


            st.markdown("---")

            col1, col2 = st.columns([4, 1])

            with col1:
                user_input = st.text_input(
                    "Ask anything...",
                    placeholder="e.g., How can I improve engagement on Instagram?",
                    key="main_chat_input"
                )

            with col2:
                st.markdown("<br>", unsafe_allow_html=True)
                send_button = st.button("Send 📤", key="send_chat")

            latest_answer = None
            if send_button and user_input:
                with st.spinner("AI is thinking..."):
                    response = generator.ai_chat_assistant(user_input, context=True)
                    st.session_state.chat_history.append({'role': 'user', 'message': user_input})
                    st.session_state.chat_history.append({'role': 'assistant', 'message': response})
                    latest_answer = response
                    st.rerun()

            if st.session_state.chat_history:
                for msg in reversed(st.session_state.chat_history):
                    if msg['role'] == 'assistant':
                        latest_answer = msg['message']
                        break
            if latest_answer:
                st.markdown(f"**Latest Assistant Answer:**\n\n{latest_answer}")

            st.markdown("**Quick Actions:**")
            quick_cols = st.columns(4)

            with quick_cols[0]:
                if st.button("💡 Content Ideas"):
                    response = generator.ai_chat_assistant("Give me 5 new content ideas for my campaign", context=True)
                    st.rerun()

            with quick_cols[1]:
                if st.button("📊 Improve Performance"):
                    response = generator.ai_chat_assistant("How can I improve my campaign performance?", context=True)
                    st.rerun()

            with quick_cols[2]:
                if st.button("🎯 Target Audience"):
                    response = generator.ai_chat_assistant("Who should I target with this campaign?", context=True)
                    st.rerun()

            with quick_cols[3]:
                if st.button("⏰ Best Times"):
                    response = generator.ai_chat_assistant("When is the best time to post on my selected platforms?", context=True)
                    st.rerun()

        with tab10:
            st.header("📚 Brand Memory Database")

            st.write("View all generated campaigns stored in the Excel database.")

            if st.session_state.campaigns:
                campaigns_df = pd.DataFrame([
                    {
                        'ID': c['id'],
                        'Brand': c['brand_info'].get('brand_name', ''),
                        'Created': c['created_at'].strftime('%Y-%m-%d %H:%M'),
                        'Platforms': ', '.join(c.get('selected_platforms', [])),
                        'Content Types': ', '.join(c.get('content', {}).keys()),
                        'Tone': c.get('tone', ''),
                    }
                    for c in st.session_state.campaigns
                ])

                st.dataframe(campaigns_df, use_container_width=True)

                if st.button("📥 Download Full Database"):
                    buffer = BytesIO()
                    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                        campaigns_df.to_excel(writer, sheet_name='Campaigns', index=False)
                    buffer.seek(0)
                    st.download_button(
                        "Download Excel Database",
                        data=buffer,
                        file_name="campaign_database.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
            else:
                st.info("No campaigns in database yet. Generate your first campaign!")


if __name__ == "__main__":
    main()