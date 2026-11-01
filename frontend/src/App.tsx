import { useEffect, useState } from 'react';

type Task = 'sentiment' | 'topics' | 'analyze';
type Score = {id: number; label: string; score: number};
type Prediction = {task: string; label: string; label_fa: string; confidence: number; scores: Score[]; model: string; revision: string; inference_ms: number; confidence_calibrated: boolean};
type Result = Prediction | {sentiment: Prediction; topics: Prediction; request_id: string};
type Meta = {models: Record<string, {model: string; revision: string; labels: string[]; max_tokens: number}>};
const examples = [
  {title:'نظر مشتری', text:'کیفیت این محصول عالی بود، ارسال سریع انجام شد و کاملاً راضی هستم.'},
  {title:'خبر فناوری', text:'پژوهشگران ایرانی از یک سامانه جدید هوش مصنوعی برای تحلیل داده‌های پزشکی رونمایی کردند.'},
  {title:'بازخورد منفی', text:'متأسفانه خدمات پشتیبانی خیلی ضعیف بود و پاسخ درستی دریافت نکردم.'}
];
const fmt = (n: number) => `${(n * 100).toFixed(1)}٪`;
const labelDisplay = (label: string) => ({Negative:'منفی',Neutral:'خنثی',Positive:'مثبت'}[label] || label);

function ScoreBoard({prediction}: {prediction:Prediction}) {
  const isSentiment = prediction.task === 'sentiment';
  return <div className="result-card">
    <div className="result-head"><span className="result-type">{isSentiment?'تحلیل احساس':'طبقه‌بندی موضوع'}</span><span className="meta-badge">ONNX • CPU</span></div>
    <div className="result-prediction"><div><span className="result-subtitle">برچسب تشخیص داده‌شده</span><h3>{prediction.label_fa || labelDisplay(prediction.label)}</h3></div><div className="confidence"><strong>{fmt(prediction.confidence)}</strong><span>میزان اطمینان مدل</span></div></div>
    <div className="scores-title">توزیع احتمال کلاس‌ها</div>
    <div className="score-list">{[...prediction.scores].sort((a,b)=>b.score-a.score).map(item=><div className="score" key={item.id}><div className="score-text"><span>{labelDisplay(item.label)}</span><b>{fmt(item.score)}</b></div><div className="bar"><div style={{width:`${item.score*100}%`}} className={isSentiment?'bar-sentiment':'bar-topic'}/></div></div>)}</div>
    <div className="result-foot"><span>مدل: <code dir="ltr">{prediction.model}</code></span><span>{prediction.inference_ms.toFixed(1)} ms • زمان استنتاج</span></div>
    <div className="notice">این امتیازها احتمال مدل هستند، نه معیار اطمینان کالیبره‌شده یا حقیقت قطعی.</div>
  </div>
}

export default function App() {
  const [task,setTask]=useState<Task>('analyze');
  const [text,setText]=useState(examples[0].text);
  const [result,setResult]=useState<Result|null>(null);
  const [error,setError]=useState('');
  const [loading,setLoading]=useState(false);
  const [status,setStatus]=useState<'checking'|'ready'|'offline'>('checking');
  const [meta,setMeta]=useState<Meta|null>(null);
  const [showApi,setShowApi]=useState(false);
  useEffect(()=>{let live=true; Promise.all([fetch('/api/health/ready'),fetch('/api/v1/models')]).then(async ([health,models])=>{if(!live)return;setStatus(health.ok?'ready':'offline');if(models.ok)setMeta(await models.json());}).catch(()=>{if(live)setStatus('offline')});return()=>{live=false}},[]);
  async function run() {
    if(!text.trim()) {setError('لطفاً متنی وارد کنید.');return}
    setLoading(true);setError('');setResult(null);
    try {
      const response=await fetch(`/api/v1/${task==='topics'?'topics':task}`, {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text})});
      if(!response.ok) {const data=await response.json().catch(()=>({detail:'خطا در ارتباط با سرویس'}));throw new Error(typeof data.detail==='string'?data.detail:`خطای سرور (${response.status})`)}
      const data=await response.json();setResult(data);
    } catch (e) {setError(e instanceof Error?e.message:'خطای ناشناخته در سرویس')}
    finally {setLoading(false)}
  }
  const predictions: Prediction[] = !result?[]:'sentiment' in result && 'topics' in result?[result.sentiment,result.topics]:[result as Prediction];
  return <div className="app-shell">
    <div className="glow glow-1"/><div className="glow glow-2"/>
    <header className="topbar"><div className="brand"><div className="brand-mark">S<span>✦</span></div><div><strong>SuperApp</strong><small>PERSIAN INTELLIGENCE</small></div></div><div className="top-actions"><span className={`health ${status}`}><i/>{status==='ready'?'سرویس آماده است':status==='checking'?'در حال بررسی...':'سرویس در دسترس نیست'}</span><a href="#workspace" className="header-action">شروع تحلیل <span>←</span></a></div></header>
    <main><section className="hero"><div className="eyebrow"><span className="pulse"/> AI TEXT ENGINE · MODULE 02</div><h1>هوش متن، <em>به زبان فارسی</em></h1><p>احساس پنهان پشت کلمات را کشف کنید؛ موضوع متن را هوشمندانه بشناسید. دو مدل تخصصی فارسی در یک محیط سریع و یکپارچه.</p><div className="hero-tags"><span>تحلیل احساسات</span><span>طبقه‌بندی موضوعی</span><span>پردازش محلی روی CPU</span></div></section>
    <section id="workspace" className="workspace"><div className="section-label"><span>۰۱ / فضای کار</span><span className="line"/>تحلیل متن</div>
    <div className="workspace-card"><div className="card-top"><div><h2>متن خود را تحلیل کنید</h2><p>یکی از روش‌های تحلیل را انتخاب و متن فارسی را وارد کنید.</p></div><span className="chip">دو مدل اختصاصی</span></div>
    <div className="tabs" role="tablist" aria-label="نوع تحلیل">{([{key:'analyze',title:'تحلیل کامل',detail:'احساس + موضوع'},{key:'sentiment',title:'تحلیل احساس',detail:'مثبت، منفی، خنثی'},{key:'topics',title:'طبقه‌بندی موضوع',detail:'۸ موضوع خبری'}] as {key:Task,title:string,detail:string}[]).map(t=><button type="button" role="tab" aria-selected={task===t.key} className={task===t.key?'selected':''} key={t.key} onClick={()=>{setTask(t.key);setResult(null);setError('')}}><strong>{t.title}</strong><small>{t.detail}</small></button>)}</div>
    <label htmlFor="textinput" className="field-title">متن فارسی</label><div className="editor"><textarea id="textinput" dir="rtl" maxLength={5000} placeholder="متن، نظر مشتری یا بخشی از یک خبر را اینجا وارد کنید..." value={text} onChange={e=>setText(e.target.value)}/><div className="editor-foot"><span>پشتیبانی از فارسی، نیم‌فاصله و متن ترکیبی</span><span>{text.length.toLocaleString('fa-IR')} / ۵۰۰۰</span></div></div>
    <div className="example-row"><span>نمونه‌های آماده:</span>{examples.map(ex=><button key={ex.title} type="button" onClick={()=>{setText(ex.text);setResult(null);setError('')}}>{ex.title} ↗</button>)}</div>
    {error&&<div role="alert" className="error">{error}</div>}
    <div className="action-row"><button className="primary-btn" onClick={run} disabled={loading||!text.trim()||status==='offline'}>{loading?<><span className="spinner"/> در حال پردازش...</>:<>✦ شروع تحلیل هوشمند <span>←</span></>}</button><span>پردازش بدون ارسال متن به سرویس‌های AI خارجی</span></div>
    </div></section>
    {predictions.length>0&&<section className="results"><div className="section-label"><span>۰۲ / خروجی</span><span className="line"/>نتایج تحلیل</div><div className="result-grid">{predictions.map((p,i)=><ScoreBoard key={i} prediction={p}/>)}</div></section>}
    <section className="info-section"><div className="section-label"><span>۰۳ / فناوری</span><span className="line"/>زیرساخت</div><div className="info-grid"><div><span className="info-icon">◉</span><h3>مدل‌های تخصصی فارسی</h3><p>مدل‌های ALBERT با برچسب‌های معتبر و قابل رهگیری از Hugging Face.</p></div><div><span className="info-icon">⚡</span><h3>CPU-first و آفلاین</h3><p>مدل پس از دریافت و آماده‌سازی، به‌طور محلی و با ONNX Runtime اجرا می‌شود.</p></div><div><span className="info-icon">◇</span><h3>API آماده ادغام</h3><p>مسیرهای نسخه‌دار، JSON ساختاریافته، مدل‌های مستقل و کنترل منابع.</p></div></div></section>
    <section className="api-section"><button className="api-toggle" type="button" onClick={()=>setShowApi(!showApi)} aria-expanded={showApi}><span>◧ راهنمای سریع API و مدل‌ها</span><span>{showApi?'−':'+'}</span></button>{showApi&&<div className="api-body"><pre dir="ltr">POST /api/v1/sentiment{'\n'}POST /api/v1/topics{'\n'}POST /api/v1/analyze{'\n'}POST /api/v1/batch{'\n'}GET  /api/v1/models</pre><p>{meta?Object.values(meta.models).map(m=>m.model).join(' · '):'فهرست مدل‌ها پس از اتصال سرویس نمایش داده می‌شود.'}</p><p>برای ادغام مستقیم سمت سرور از Header به نام X-API-Key استفاده کنید. رابط عمومی نیازمند احراز هویت در Ingress است.</p></div>}</section>
    </main><footer><span>© 2026 SuperApp · Persian NLP</span><span>Designed for accurate, responsible AI inference</span></footer>
  </div>
}
