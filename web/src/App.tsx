import { useEffect, useState } from 'react'
import { Plus, ChevronRight, ArrowUpRight, FileText, Check, Circle, RefreshCw, ArrowLeft, BookOpen, MessageSquare, PanelLeft, LockKeyhole } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog'
import type { Project, Snapshot, Topic } from './types'

const stages = ['点子与资产','定位与研究','故事与流程','需求与体验','架构与安全','路线与任务','一致性审查']
const questions:Record<string,string> = {audience:'谁会使用，在什么情况下使用？',problem:'现在最需要解决的具体问题是什么？',success:'第一版做到什么，才算有用？'}
const labels:Record<string,string> = {'00-idea-brief':'原始点子简报','00-asset-recall':'历史资产回收','01-product-research':'产品定位与研究','02-stories-and-journeys':'用户故事与旅程','02-state-machines':'状态与异常流程','03-prd':'产品需求文档','03-design-system':'设计系统','04-architecture':'系统架构','04-technology-decisions':'技术决策','04-security-threat-model':'安全威胁模型','05-roadmap':'产品路线图','06-task-board':'任务看板','05-definition-of-done':'完成标准','07-consistency-audit':'一致性审查','08-engineering-handoff':'工程交接','07-security-acceptance-plan':'安全验收计划'}
const docName = (path:string) => labels[path.split('/').pop()!.replace('.md','')] || path
const verdicts:Record<string,string> = {support:'支持',concern:'存疑',oppose:'反对',adopt:'采纳',revise:'修订',defer:'暂缓',reject:'拒绝',pass:'通过',changes:'需修改',blocked:'受阻'}
let token = ''
async function request(path:string, body?:unknown) {
  const response = await fetch(path, body ? {method:'POST',headers:{'Content-Type':'application/json','X-Foundry-Token':token},body:JSON.stringify(body)} : {})
  const data = await response.json()
  if (!response.ok) throw new Error(data.error || '请求失败，请刷新重试')
  return data
}
function Markdown({text}:{text:string}) {
  return <div className="manuscript">{text.split('\n').map((line,i) => line.startsWith('# ') ? <h1 key={i}>{line.slice(2)}</h1> : line.startsWith('## ') ? <h2 key={i}>{line.slice(3)}</h2> : line.startsWith('### ') ? <h3 key={i}>{line.slice(4)}</h3> : <p key={i}>{line || '\u00a0'}</p>)}</div>
}
const Field=({name,label,area=false,defaultValue='',placeholder=''}:{name:string;label:string;area?:boolean;defaultValue?:string;placeholder?:string})=><label className="field"><span>{label}</span>{area?<Textarea name={name} required defaultValue={defaultValue} placeholder={placeholder} rows={3}/>:<Input name={name} required defaultValue={defaultValue} placeholder={placeholder}/>}</label>
export default function App() {
  const [projects,setProjects] = useState<Project[]>([])
  const [project,setProject] = useState<Snapshot|null>(null)
  const [stage,setStage] = useState(0)
  const [tab,setTab] = useState('work')
  const [doc,setDoc] = useState('')
  const [content,setContent] = useState('')
  const [original,setOriginal] = useState('')
  const [editing,setEditing] = useState(false)
  const [docValid,setDocValid] = useState(false)
  const [docHash,setDocHash] = useState('')
  const [busy,setBusy] = useState(false)
  const [booting,setBooting] = useState(true)
  const [error,setError] = useState('')
  const [notice,setNotice] = useState('')
  const [modal,setModal] = useState('')
  const [nav,setNav] = useState(false)
  const [topic,setTopic] = useState<Topic|null>(null)
  const [answers,setAnswers] = useState<Record<string,string>>({})
  const [sources,setSources] = useState<{id:string;repository:string;commit:string;source_path:string;sha256:string;source_url:string}[]>([])
  const dirty = content !== original
  const unsavedAnswers = !!project && Object.keys(questions).some(key=>(answers[key]||'')!==(project.answers[key]||''))
  function leaveDraft() { if(dirty||unsavedAnswers) {setError(dirty?'文档有未保存修改，请先保存或撤销。':'回答有未保存修改，请先保存。'); return false} return true }
  async function select(id:string) {
    if(!leaveDraft()) return
    const data:Snapshot = await request('/api/projects/'+id)
    localStorage.setItem('foundry-project',id)
    setProject(data); setAnswers(data.answers); setStage(data.status.current_stage ?? 6); setDoc(''); setContent(''); setOriginal(''); setTab('work'); setNav(false)
  }
  async function refresh() {
    setProjects(await request('/api/projects'))
    if(project) { const data = await request('/api/projects/'+project.id); setProject(data); setAnswers(data.answers) }
  }
  useEffect(() => {
    (async()=>{try { token = (await request('/api/session')).token; const list = await request('/api/projects'); setProjects(list); setSources((await request('/api/sources')).assets); if(list.length) await select(list.find((p:Project)=>p.id===localStorage.getItem('foundry-project'))?.id || list[0].id) } catch(e){setError((e as Error).message)} finally {setBooting(false)} })()
  },[])
  useEffect(()=>{ const handler=(e:BeforeUnloadEvent)=>{if(dirty||unsavedAnswers){e.preventDefault();e.returnValue=''}}; window.addEventListener('beforeunload',handler); return()=>window.removeEventListener('beforeunload',handler) },[dirty,unsavedAnswers])
  async function run(work:()=>Promise<void>) {setBusy(true);setError('');setNotice('');try{await work()}catch(e){setError((e as Error).message)}finally{setBusy(false)}}
  async function action(body:Record<string,unknown>) {
    const data:Snapshot = await request('/api/projects/'+project!.id+'/actions',{...body,revision:project!.status.revision})
    setProject(data); setProjects(await request('/api/projects')); return data
  }
  async function openDoc(path:string) {
    if(!leaveDraft()) return
    await run(async()=>{const data=await request('/api/projects/'+project!.id+'/document?path='+encodeURIComponent(path));setDoc(path);setContent(data.content);setOriginal(data.content);setDocValid(data.valid);setDocHash(data.sha256||'');setEditing(!data.content);setTab('documents')})
  }
  function changeTab(value:string) {if(leaveDraft())setTab(value)}
  const active = project?.status.current_stage
  const gate = project?.status.stage_gate
  const current = stage === active
  const docs = project?.documents[String(stage)] || []
  const selectedStage = project?.stages[stage]
  const ready = !!gate && !gate.missing_artifacts.length && !gate.unanswered.length && gate.passing_review && !gate.blocking_review && !gate.open_agent_tasks.length && !gate.open_panel_topics.length && (!gate.security_gate || gate.security_gate.design_ready)
  const openTopics = project?.topics.filter(t=>t.status==='open') || []
  const fields = (form:HTMLFormElement) => Object.fromEntries(new FormData(form).entries()) as Record<string,string>
  async function sendForm(e:React.FormEvent<HTMLFormElement>) {
    e.preventDefault();const values=fields(e.currentTarget)
    await run(async()=>{
      if(modal==='new'){ const data=await request('/api/projects',values);localStorage.setItem('foundry-project',data.id);setProjects(await request('/api/projects'));setProject(data);setAnswers(data.answers);setStage(0);setDoc('');setContent('');setOriginal('');setTab('work') }
      else {const kind=modal==='opinion'?'panel-opinion':modal==='resolve'?'panel-resolve':modal==='topic'?'panel-open':modal; const data=await action({action:kind,...values,id:topic?.id});if(modal==='confirm'){setStage(data.status.current_stage??6);setTab('work');setDoc('')} }
      setModal('');setNotice('已记录到当前项目。')
    })
  }

  return <div className="app-shell">
    <a className="skip" href="#main">跳到工作区</a>
    <aside className={'sidebar '+(nav?'nav-open':'')} aria-label="项目与阶段">
      <div className="brand"><span className="brand-mark">P<span>／</span></span><strong>Prism</strong><span className="version">FOUNDRY .03</span></div>
      <div className="sidebar-heading"><span>项目目录</span><Button variant="ghost" size="icon" aria-label="新建项目" onClick={()=>{if(leaveDraft())setModal('new')}}><Plus size={15}/></Button></div>
      <div className="project-list">{projects.map(p=><button key={p.id} className={'project-link '+(p.id===project?.id?'selected':'')} onClick={()=>run(()=>select(p.id))}><span className="project-dot"/><span>{p.idea}</span><ChevronRight size={13}/></button>)}{!projects.length&&<p className="muted sidebar-note">尚无项目。先记下一个点子。</p>}</div>
      <div className="sidebar-heading stages-heading">推演阶段</div>
      <nav>{stages.map((name,i)=><button key={name} disabled={!project} className={'stage-link '+(stage===i?'active':'')} onClick={()=>{if(leaveDraft()){setStage(i);setDoc('');setTab('work');setNav(false)}}}><span className="stage-number">{project?.stages[i].confirmed?<Check size={13}/>:String(i).padStart(2,'0')}</span><span>{name}</span>{i===active&&<span className="stage-now">当前</span>}</button>)}</nav>
      <div className="sidebar-bottom"><LockKeyhole size={14}/><div>本机工作区<span>Agent 尚未启动 · 发布未授权</span></div></div>
    </aside>
    <div className="workspace">
      <header className="topbar"><Button variant="ghost" size="icon" className="mobile-menu" aria-label="展开项目导航" onClick={()=>setNav(!nav)}><PanelLeft size={18}/></Button><div className="breadcrumb">工作台 <ChevronRight size={12}/><span>{project?'阶段 '+stage+' · '+stages[stage]:'新的起点'}</span></div><div className="top-actions"><span className="revision">{project?'修订 '+project.status.revision:'本地保存'}</span><Button variant="ghost" size="icon" disabled={busy||dirty||unsavedAnswers} aria-label="刷新项目" onClick={()=>run(refresh)}><RefreshCw size={15}/></Button></div></header>
      {error&&!modal&&<div role="alert" className="message error"><span>{error}</span><Button variant="ghost" size="sm" onClick={()=>setError('')}>关闭</Button></div>}
      {notice&&<div role="status" className="message success">{notice}</div>}
      {booting?<main id="main" className="welcome"><p>正在读取本机项目…</p></main>:!project?<main id="main" className="welcome"><div className="welcome-index">Prism / Product Foundry</div><h1>从一个点子，<br/>到一份有依据的决定。</h1><p>先说清要解决的问题。把资料、争议和每次确认，<br/>留在同一条推演主线上。</p><Button onClick={()=>setModal('new')}>记下第一个点子 <Plus size={16}/></Button><div className="welcome-foot">七个阶段 · 逐项审查 · 明确确认</div></main>:<div className="work-grid">
      <main id="main" className="main-column">
        <section className="project-heading"><div className="project-meta"><span>{selectedStage?.confirmed?'已确认':current?'正在推演':'待进入'} / 阶段 {String(stage).padStart(2,'0')}</span><span>{project.stages.filter(s=>s.confirmed).length} / 7 阶段已确认</span></div><h1>{project.status.original_intent}</h1><p>把问题说清楚，再决定往哪里走。</p></section>
        <Tabs value={tab} onValueChange={changeTab} className="workspace-tabs"><TabsList className="tab-list"><TabsTrigger value="work">阶段工作</TabsTrigger><TabsTrigger value="documents">文档 <span>{docs.length}</span></TabsTrigger><TabsTrigger value="discussion">专家讨论 <span>{project.topics.filter(t=>t.stage===stage).length}</span></TabsTrigger><TabsTrigger value="sources">证据来源</TabsTrigger></TabsList>
        <TabsContent value="work" className="tab-body">
          <div className="section-heading"><h2>{stages[stage]}</h2><span className="muted">{current?'当前阶段':'阶段档案'}</span></div>
          {stage===0?<section className="questions"><p className="section-intro">三个问题，确定这次推演的边界。</p>{Object.entries(questions).map(([key,label],i)=><div className="question" key={key}><span className="item-number">0{i+1}</span><div><label htmlFor={key}>{label}</label><Textarea id={key} value={answers[key]||''} onChange={e=>setAnswers({...answers,[key]:e.target.value})} readOnly={!current} placeholder="用具体的人、场景和结果描述" rows={2}/><div className="answer-bottom"><span>{project.answers[key]?'已有记录':'待补充'}</span>{current&&<Button variant="ghost" size="sm" disabled={busy||!answers[key]?.trim()||answers[key]===project.answers[key]} onClick={()=>run(async()=>{await action({action:'answer',key,value:answers[key],actor:'本机用户'});setNotice('答案已保存。')})}>保存回答 <ArrowUpRight size={13}/></Button>}</div></div></div>)}</section>:<p className="section-intro">按当前阶段合同提交文档，记录审查意见。完成本阶段后，由项目负责人明确确认。</p>}
          <section className="document-index"><div className="section-heading"><h2>本阶段文档</h2><span className="muted">{docs.filter(p=>project.artifact_validity[p]).length} / {docs.length} 已提交</span></div>{docs.map(path=><button className="document-row" key={path} onClick={()=>openDoc(path)}><FileText size={17}/><div><strong>{docName(path)}</strong><span>{path}</span></div><span className="doc-state">{project.artifact_validity[path]?'已提交':selectedStage?.artifacts[path]?'待重新提交':'待编写'}</span><ArrowUpRight size={15}/></button>)}</section>
          <div className="stage-note"><BookOpen size={16}/><p>阶段标准来自集团固定版本的 idea-to-blueprint。<button onClick={()=>setTab('sources')}>查看来源</button></p></div>
        </TabsContent>
        <TabsContent value="documents" className="tab-body document-tab">{!doc?<><h2>文档目录</h2><p className="section-intro">选择一份文档，查看当前提交版本或补充内容。</p>{docs.map(path=><button className="document-row" key={path} onClick={()=>openDoc(path)}><FileText size={17}/><div><strong>{docName(path)}</strong><span>{path}</span></div><ArrowUpRight size={15}/></button>)}</>:<><div className="editor-toolbar"><Button variant="ghost" size="sm" onClick={()=>{if(leaveDraft())setDoc('')}}><ArrowLeft size={14}/>目录</Button><div><Button variant={!editing?'secondary':'ghost'} size="sm" onClick={()=>setEditing(false)}>预览</Button><Button variant={editing?'secondary':'ghost'} size="sm" disabled={!current} onClick={()=>setEditing(true)}>编辑</Button></div></div><div className="document-caption"><h2>{docName(doc)}</h2><span>{selectedStage?.artifacts[doc]?(docValid?'提交 r'+selectedStage.artifacts[doc].revision:'版本已变更，待重新提交'):'未提交'}{dirty?' · 有未保存修改':''}</span></div>{editing?<><Textarea aria-label="文档正文" className="document-editor" value={content} onChange={e=>setContent(e.target.value)} placeholder="写下已知事实、依据和待确认项。Markdown 基础预览支持标题与段落。"/><div className="save-row"><Button variant="ghost" disabled={!dirty||busy} onClick={()=>setContent(original)}>撤销修改</Button><Button disabled={!dirty||!content.trim()||busy} onClick={()=>run(async()=>{const saved=await action({action:'submit',path:doc,content,actor:'本机用户'});setOriginal(content);setDocValid(true);setDocHash(saved.stages[stage].artifacts[doc].sha256);setNotice('文档已提交；本阶段需要重新审查。')})}>提交文档</Button></div></>:content?<Markdown text={content}/>:<div className="empty-state"><FileText size={24}/><h3>这份文档还没有内容</h3><p>{current?'切换到编辑，记录事实与依据。':'该阶段尚未提交文档。'}</p></div>}{selectedStage?.artifacts[doc]&&<div className="document-provenance"><span>提交者声明：{selectedStage.artifacts[doc].actor}</span><code>登记 SHA256 {selectedStage.artifacts[doc].sha256}</code>{!docValid&&<code>当前 SHA256 {docHash}</code>}</div>}</>}</TabsContent>
        <TabsContent value="discussion" className="tab-body"><div className="section-heading"><h2>让分歧留下来</h2><Button size="sm" variant="outline" disabled={!current||busy} onClick={()=>setModal('topic')}><Plus size={14}/>提出议题</Button></div><p className="section-intro">意见由人手动录入。角色与姓名为声明，不代表已执行真实 Agent。</p>{project.topics.filter(t=>t.stage===stage).map(t=><article key={t.id} className="topic"><div className="topic-meta"><span>{t.id}</span><span>{t.status==='open'?'待裁决':t.status==='resolved'?'已裁决':'已失效'}</span></div><h3>{t.question}</h3>{t.opinions.map((o,i)=><div className="opinion" key={i}><div><strong>{o.role}</strong><span>{verdicts[o.verdict]} · {o.actor_claim}</span></div><p>{o.reasoning}</p><dl><dt>依据</dt><dd>{o.evidence}</dd><dt>反例</dt><dd>{o.counterexample}</dd></dl><small>来源未核验 · 身份未认证</small></div>)}{!t.opinions.length&&<p className="muted">还没有意见。至少记录一份包含质疑的意见后，才能裁决。</p>}{t.resolution&&<div className="resolution">{verdicts[t.resolution.outcome]}：{t.resolution.rationale}</div>}{t.status==='open'&&current&&<div className="topic-actions"><Button size="sm" variant="outline" onClick={()=>{setTopic(t);setModal('opinion')}}>记录意见</Button><Button size="sm" variant="ghost" onClick={()=>{setTopic(t);setModal('resolve')}}>作出裁决 <ChevronRight size={13}/></Button></div>}</article>)}{!project.topics.some(t=>t.stage===stage)&&<div className="empty-state"><MessageSquare size={26}/><h3>尚无专家讨论</h3><p>先提出一个需要不同视角判断的具体问题。</p></div>}</TabsContent>
        <TabsContent value="sources" className="tab-body"><h2>依据从哪里来</h2><p className="section-intro">下列是规划合同的固定来源，不等于已完成用户研究。产品研究证据写入阶段文档，专家依据见讨论原文。</p>{sources.map(s=><article className="source" key={s.id}><span className="source-type">固定方法合同</span><h3>{s.id}</h3><p>{s.repository} / {s.source_path}</p><code>{s.commit}</code><a href={s.source_url} target="_blank" rel="noreferrer">查看固定版本 <ArrowUpRight size={13}/></a></article>)}</TabsContent>
        </Tabs>
      </main>
      <aside className="review-column" aria-label="决策与审查"><div className="review-heading"><h2>决策与审查</h2><span className="review-dot"/></div><section className="review-section"><div className="section-heading"><h3>待决策</h3><span>{openTopics.length}</span></div>{openTopics.length?openTopics.map(t=><button className="decision-link" key={t.id} onClick={()=>{if(leaveDraft()){setStage(t.stage);setTab('discussion')}}}><span>{t.id}</span><strong>{t.question}</strong><small>{t.opinions.length} 份意见 <ArrowUpRight size={13}/></small></button>):<p className="muted">暂无未决议题。新的分歧可在专家讨论中提出。</p>}{project.changes.filter(c=>c.status==='proposed').map(c=><p key={c.id}>待处理变更 {c.id}：{c.description}（通过原 CLI 裁决）</p>)}</section><section className="review-section"><h3>阶段 {active??'—'} 确认条件</h3>{!current&&active!==null&&<button className="return-current" onClick={()=>{if(leaveDraft()){setStage(active??0);setDoc('');setTab('work')}}}>返回当前阶段 {active}，再记录审查</button>}{gate?<ul className="gate-list"><li><span>{!gate.unanswered.length?<Check/>:<Circle/>}</span>关键问题已回答</li><li><span>{!gate.missing_artifacts.length?<Check/>:<Circle/>}</span>文档齐全且版本有效</li><li><span>{gate.passing_review&&!gate.blocking_review?<Check/>:<Circle/>}</span>本阶段审查通过</li><li><span>{!gate.open_panel_topics.length&&!gate.open_agent_tasks.length?<Check/>:<Circle/>}</span>争议与任务已处理</li><li><span>{!gate.security_gate?<LockKeyhole/>:gate.security_gate.design_ready?<Check/>:<Circle/>}</span>{gate.security_gate?'安全设计门禁':'安全设计在阶段 4 确认'}</li></ul>:<p>全部阶段已确认。工程执行与发布仍需单独授权。</p>}{project.status.integrity_issues.length>0&&<p className="integrity">发现已确认文档版本失效，请通过变更流程重新审查。</p>}<Button className="full-width" variant="outline" disabled={busy||active===null||!current} onClick={()=>setModal('review')}>记录本阶段审查</Button><Button className="full-width confirm" disabled={busy||!ready||!current||project.status.integrity_issues.length>0} onClick={()=>{if(leaveDraft())setModal('confirm')}}>确认阶段 {active??'—'} <ChevronRight size={14}/></Button><p className="approval-note">确认针对当前修订 {project.status.revision}。<br/>本机身份声明，尚未接入身份认证。</p></section><section className="review-section"><h3>审查记录</h3>{project.stages[active??6].reviews.length?project.stages[active??6].reviews.slice(-3).map((r,i)=><div className="review-record" key={i}><strong>{verdicts[r.verdict]} · {r.actor}</strong><p>{r.note}</p><small>自检声明 / 非独立验收</small></div>):<p className="muted">尚无审查记录。</p>}</section><div className="review-footer">规划确认不会启动工程、付费调用或发布。</div></aside>
      </div>}
    </div>
    <Dialog open={!!modal} onOpenChange={open=>{if(!busy&&!open)setModal('')}}><DialogContent className="foundry-dialog"><DialogHeader><DialogTitle>{{new:'记下一个点子',review:'记录阶段 '+active+' 审查',confirm:'确认当前阶段',topic:'提出一个议题',opinion:'记录一份意见',resolve:'裁决议题'}[modal]}</DialogTitle><DialogDescription>{modal==='new'?'保留最初的想法，后续修改通过阶段文档和变更记录推进。':'记录到当前项目版本。身份均为本机声明，不能替代独立验收。'}</DialogDescription></DialogHeader><form onSubmit={sendForm} key={modal}>
      {modal==='new'&&<Field name="idea" label="你的点子" area placeholder="想为谁，解决什么问题？"/>}
      {modal==='topic'&&<Field name="question" label="要讨论的具体问题" area/>}
      {modal==='review'&&<><label className="field">审查结论<select name="verdict" aria-label="审查结论"><option value="changes">需要修改</option><option value="blocked">受阻</option><option value="pass">通过自检</option></select></label><Field name="note" label="检查了什么，依据是什么？" area/></>}
      {modal==='confirm'&&<><p>确认阶段 {active}「{stages[active??0]}」的当前文档和审查记录，进入下一阶段。</p><Field name="statement" label="明确确认声明" area placeholder="说明本次确认的范围与依据"/></>}
      {modal==='opinion'&&<><div className="form-pair"><label className="field">角色<select name="role" aria-label="角色">{['pm','research','ux','architect','security','qa','challenger'].map(r=><option key={r}>{r}</option>)}</select></label><label className="field">立场<select name="verdict" aria-label="立场"><option value="concern">存疑</option><option value="support">支持</option><option value="oppose">反对</option></select></label></div><label className="field">严重程度<select name="severity" aria-label="严重程度"><option value="medium">中</option><option value="high">高</option><option value="critical">严重</option><option value="info">信息</option></select></label><Field name="reasoning" label="判断与理由" area/><Field name="evidence" label="依据 / 来源（未核验）" area/><Field name="counterexample" label="什么反例会推翻这个判断？" area/></>}
      {modal==='resolve'&&<><p>{topic?.question}</p><label className="field">裁决<select name="outcome" aria-label="裁决"><option value="defer">暂缓</option><option value="adopt">采纳</option><option value="revise">修订</option><option value="reject">拒绝</option></select></label><Field name="rationale" label="裁决依据" area/></>}
      <Field name="actor" label="记录人 / 身份声明" defaultValue="本机用户"/>{error&&<p role="alert" className="message error">{error}</p>}<div className="dialog-actions"><Button type="button" variant="ghost" disabled={busy} onClick={()=>setModal('')}>取消</Button><Button type="submit" disabled={busy}>{busy?'保存中…':modal==='confirm'?'记录确认':'保存记录'}</Button></div>
    </form></DialogContent></Dialog>
  </div>
}
