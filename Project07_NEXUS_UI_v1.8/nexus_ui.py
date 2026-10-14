"""NEXUS presentation layer. No changes to backend authorization or review gates."""
import base64
import html
from contextlib import contextmanager
from pathlib import Path
import streamlit as st

LOGO = 'data:image/png;base64,' + base64.b64encode((Path(__file__).parent / 'assets/nexus-logo.png').read_bytes()).decode()
PAGES = ['Trang chủ', 'Bảo vệ dữ liệu', 'Dữ liệu & Audit Run', 'RCM', 'Test Plan', 'Tests & Exceptions', 'Findings', 'Report', 'Evaluation', 'Vai trò & cấu hình']

@contextmanager
def loading(message='Đang xử lý dữ liệu…'):
    slot = st.empty()
    slot.markdown(f'<div class="nx-loading" role="status" aria-live="polite"><img src="{LOGO}" alt="NEXUS đang xử lý"><div><strong>{html.escape(message)}</strong><br><span>Vui lòng giữ trang này mở</span></div></div>', unsafe_allow_html=True)
    try:
        yield
    finally:
        slot.empty()

def shell():
    dark = st.sidebar.toggle('Chế độ tối · Dark', value=True, key='nx_dark')
    if dark:
        colors = '--bg:#08151d;--panel:#10232e;--input:#15303d;--text:#ecf4f7;--muted:#acc2cd;--line:#2b4553;--accent:#59d6de;--gold:#eed194;--shadow:#0006;'
    else:
        colors = '--bg:#f3f6f8;--panel:#ffffff;--input:#edf3f6;--text:#152d3a;--muted:#516b79;--line:#ccdae2;--accent:#087983;--gold:#86601d;--shadow:#203d5114;'
    st.markdown('''<style>
    :root{COLORS color-scheme:SCHEME;}
    html{scroll-behavior:smooth} .stApp{background:var(--bg);color:var(--text)}
    [data-testid="stHeader"]{background:var(--bg)}
    [data-testid="stSidebar"]{background:var(--panel);border-right:1px solid var(--line)}
    .block-container{max-width:1440px;padding-top:2rem;padding-bottom:3rem}
    h1,h2,h3,h4,p,label,[data-testid="stWidgetLabel"], [data-testid="stMarkdownContainer"]{color:var(--text)}
    [data-testid="stCaptionContainer"] p{color:var(--muted)}
    [data-testid="stTextInput"] input,[data-testid="stTextArea"] textarea,[data-baseweb="select"]>div{background:var(--input)!important;color:var(--text)!important;border-color:var(--line)!important}
    [data-baseweb="popover"], [data-baseweb="menu"], [role="listbox"], [role="option"]{background:var(--panel)!important;color:var(--text)!important}
    [data-testid="stForm"], [data-testid="stExpander"], [data-testid="stFileUploaderDropzone"]{background:var(--panel);border:1px solid var(--line);border-radius:16px}
    [data-testid="stFileUploaderDropzone"] *{color:var(--text)}
    [data-testid="stAlert"]{background:var(--panel);border:1px solid var(--line)}
    [data-testid="stJson"]{background:var(--panel);color:var(--text)}
    .stButton button,.stDownloadButton button,[data-testid="stFormSubmitButton"] button{border-radius:11px;min-height:44px;border:1px solid var(--line);background:var(--panel);color:var(--text);transition:transform .18s ease,box-shadow .18s ease,border-color .18s ease}
    .stButton button:hover,.stDownloadButton button:hover{transform:translateY(-2px);border-color:var(--accent);box-shadow:0 7px 20px var(--shadow);color:var(--accent)}
    button[kind="primary"]{background:#087d86!important;color:white!important;border-color:#159da5!important} button[kind="primary"] p{color:white!important}
    button:disabled{opacity:.5} button:focus-visible,a:focus-visible{outline:3px solid var(--accent)!important;outline-offset:3px}
    .nx-brand{display:flex;align-items:center;gap:18px;margin:0 0 24px}.nx-logo{width:110px;height:64px;object-fit:contain;background:white;border-radius:12px;padding:4px}
    .nx-brand strong{font-size:24px;letter-spacing:3px}.nx-brand small{display:block;color:var(--muted);font-size:12px;letter-spacing:1px;margin-top:5px}
    .nx-hero{position:relative;overflow:hidden;padding:52px;border:1px solid var(--line);border-radius:24px;background:radial-gradient(ellipse at 85% 20%,#11a2ae33,transparent 55%),linear-gradient(135deg,var(--panel),var(--bg));box-shadow:0 20px 60px var(--shadow);margin:18px 0 22px;animation:nx-enter .45s ease both}
    .nx-eyebrow{color:var(--gold);letter-spacing:2px;font-size:12px;font-weight:700}.nx-hero h1{font-size:clamp(30px,4vw,54px);line-height:1.13;max-width:850px;margin:18px 0}.nx-hero p{font-size:17px;line-height:1.7;max-width:760px;color:var(--muted)}
    .nx-tags{display:flex;gap:10px;flex-wrap:wrap;margin-top:26px}.nx-tags span{padding:7px 13px;border:1px solid var(--line);border-radius:30px;color:var(--accent);font-size:12px}
    .nx-card{background:var(--panel);border:1px solid var(--line);border-radius:18px;padding:24px;min-height:190px;margin:12px 0;transition:transform .2s,border-color .2s}.nx-card:hover{transform:translateY(-4px);border-color:var(--accent)}.nx-card b{color:var(--gold);font-size:12px;letter-spacing:2px}.nx-card h3{font-size:21px;margin:14px 0 9px}.nx-card p{color:var(--muted);line-height:1.6;font-size:14px}
    .nx-step{padding:14px 20px;background:var(--panel);border:1px solid var(--line);border-radius:12px;margin-bottom:10px}.nx-step span{color:var(--accent);font-weight:700;margin-right:15px}
    .nx-loading{position:fixed;z-index:999990;left:50%;top:38%;transform:translateX(-50%);display:flex;align-items:center;gap:22px;width:min(480px,90vw);padding:25px;background:var(--panel);color:var(--text);border:1px solid var(--accent);border-radius:20px;box-shadow:0 20px 100px #0008}.nx-loading img{width:88px;height:88px;object-fit:contain;background:white;border-radius:50%;animation:nx-spin 2.6s linear infinite}.nx-loading span{color:var(--muted);font-size:13px}
    [data-testid="stStatusWidget"] [data-testid="stSpinner"], [data-testid="stStatusWidget"] svg{display:none}
    [data-testid="stStatusWidget"]::before{content:"";display:inline-block;width:28px;height:28px;background:white url("LOGO") center/contain no-repeat;border-radius:50%;animation:nx-spin 2.6s linear infinite}
    @keyframes nx-spin{to{transform:rotate(360deg)}}@keyframes nx-enter{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:translateY(0)}}
    @media(max-width:640px){.nx-hero{padding:26px}.nx-brand strong{font-size:19px}.block-container{padding-left:1rem;padding-right:1rem}.nx-card{min-height:0}}
    @media(prefers-reduced-motion:reduce){*,*::before{animation:none!important;transition:none!important;scroll-behavior:auto!important}}
    </style>'''.replace('COLORS',colors).replace('SCHEME','dark' if dark else 'light').replace('LOGO',LOGO),unsafe_allow_html=True)
    st.markdown(f'<div class="nx-brand"><img class="nx-logo" src="{LOGO}" alt="Logo NEXUS"><div><strong>NEXUS</strong><small>AI INTERNAL AUDIT · PROJECT 07</small></div></div>',unsafe_allow_html=True)
    st.sidebar.markdown('### Không gian kiểm toán')
    page=st.sidebar.selectbox('Menu tác vụ', PAGES,key='nx_page')
    cols=st.columns(4)
    for col,title,target in zip(cols,['Trang chủ','Bảo vệ dữ liệu','Cuộc kiểm toán','Báo cáo'],['Trang chủ','Bảo vệ dữ liệu','Dữ liệu & Audit Run','Report']):
        col.button(title,key='nav_'+target,on_click=navigate,args=(target,),use_container_width=True)
    return page

def navigate(target):
    st.session_state['nx_page']=target

def home(run_count):
    st.markdown('''<section class="nx-hero"><div class="nx-eyebrow">KIỂM TOÁN CÓ CĂN CỨ</div><h1>Từ dữ liệu đến<br>góc nhìn kiểm toán.</h1><p>Một không gian để bảo vệ dữ liệu, xây dựng kế hoạch kiểm tra và kết nối từng phát hiện với bằng chứng. AI hỗ trợ phân tích. Auditor chủ động quyết định.</p><div class="nx-tags"><span>Policy → RCM</span><span>Python kiểm tra</span><span>Evidence linkage</span><span>Human review</span></div></section>''',unsafe_allow_html=True)
    cols=st.columns(3)
    cards=[('01 · DATA PRIVACY','Bảo vệ đầu vào','Thay mã thông tin nhạy cảm, giữ cấu trúc dữ liệu và tải bảng đối chiếu riêng.','Bảo vệ dữ liệu','Bảo vệ dữ liệu'),('02 · AUDIT WORKSPACE','Bắt đầu kiểm toán','Chọn chính sách, dữ liệu và bảng phân quyền để tạo một cuộc kiểm toán.','Tạo cuộc kiểm toán','Dữ liệu & Audit Run'),('03 · ASSURANCE','Theo dõi chất lượng','Đọc kết quả đánh giá, thời gian xử lý và dấu vết review của từng tác vụ.','Xem đánh giá','Evaluation')]
    for col,(tag,title,description,label,target) in zip(cols,cards):
        with col:
            st.markdown(f'<article class="nx-card"><b>{tag}</b><h3>{title}</h3><p>{description}</p></article>',unsafe_allow_html=True)
            st.button(label,key='home_'+target,on_click=navigate,args=(target,),use_container_width=True)
    st.markdown('### Quy trình trong một không gian')
    st.caption(f'{run_count} cuộc kiểm toán đã tạo · Chọn một cuộc kiểm toán trong menu bên trái để tiếp tục.')
    cols=st.columns(3)
    for i,(label,target) in enumerate([('Xây dựng RCM','RCM'),('Lập Test Plan','Test Plan'),('Kiểm tra và ngoại lệ','Tests & Exceptions'),('Review findings','Findings'),('Soạn báo cáo','Report'),('Cấu hình và vai trò','Vai trò & cấu hình')]):
        cols[i%3].button(f'{i+1:02d}  {label}',key='step_'+target,on_click=navigate,args=(target,),use_container_width=True)
    st.caption('Báo cáo được soạn ở trạng thái DRAFT và cần auditor review. Môi trường demo dùng dữ liệu giả lập.')
