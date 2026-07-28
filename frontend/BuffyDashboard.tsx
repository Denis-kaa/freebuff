import { useMemo, useState ***REMOVED*** from "react";
import {
  Search,
  Cpu,
  Brain,
  Network,
  FolderTree,
  Activity,
  Database,
  Bot,
  GitBranch,
  Sparkles,
  Bell,
  Settings,
***REMOVED*** from "lucide-react";

const nodes = [
  { id: 1, x: 42, y: 18, label: "Buffy Core", color: "#4FD1C5", size: 18 ***REMOVED***,
  { id: 2, x: 25, y: 38, label: "Knowledge", color: "#69B7FF", size: 14 ***REMOVED***,
  { id: 3, x: 61, y: 36, label: "Memory", color: "#F6C453", size: 14 ***REMOVED***,
  { id: 4, x: 73, y: 60, label: "Hermes", color: "#8B9CFF", size: 12 ***REMOVED***,
  { id: 5, x: 30, y: 68, label: "OpenClaw", color: "#FF8A65", size: 12 ***REMOVED***,
  { id: 6, x: 49, y: 80, label: "Planner", color: "#7EE081", size: 12 ***REMOVED***,
  { id: 7, x: 18, y: 57, label: "Tasks", color: "#6FD5FF", size: 12 ***REMOVED***,
***REMOVED***;

const edges = [
  [1,2***REMOVED***,[1,3***REMOVED***,[1,4***REMOVED***,[1,5***REMOVED***,[2,6***REMOVED***,[3,6***REMOVED***,[6,7***REMOVED***,[5,7***REMOVED***,[4,6***REMOVED***
***REMOVED***;

export default function BuffyDashboard(){

  const lookup = useMemo(
    ()=>Object.fromEntries(nodes.map(n=>[n.id,n***REMOVED***)),
    [***REMOVED***
  );

  const [selected,setSelected***REMOVED*** = useState(nodes[0***REMOVED***);

  return (

<div className="h-screen w-screen overflow-hidden bg-[radial-gradient(circle_at_top,#2f415e_0%,#1b2332_35%,#111723_100%)***REMOVED*** text-slate-100">

{/* soft glow */***REMOVED***

<div className="absolute inset-0 bg-[radial-gradient(circle_at_30%_20%,rgba(83,196,255,.12),transparent_35%)***REMOVED***"/>
<div className="absolute inset-0 bg-[radial-gradient(circle_at_80%_70%,rgba(77,209,197,.10),transparent_40%)***REMOVED***"/>

{/* TOP BAR */***REMOVED***

<div className="h-16 backdrop-blur-xl border-b border-white/10 flex items-center px-6">

<div className="flex items-center gap-3">
<div className="w-9 h-9 rounded-xl bg-cyan-400/20 flex items-center justify-center">
<Brain className="text-cyan-300"/>
</div>

<div>
<div className="font-semibold tracking-wide">
BUFFY
</div>
<div className="text-xs text-slate-400">
Knowledge Operating System
</div>
</div>

</div>

<div className="flex-1"/>

<div className="w-[420px***REMOVED*** rounded-xl bg-white/5 border border-white/10 flex items-center px-4 h-11">

<Search size={18***REMOVED***/>

<input
placeholder="Search memory, agents, knowledge..."
className="bg-transparent outline-none flex-1 ml-3 placeholder:text-slate-500"
/>

</div>

<div className="flex gap-4 ml-6">

<Bell/>
<Settings/>

</div>

</div>

<div className="flex h-[calc(100%-64px)***REMOVED***">

{/* LEFT */***REMOVED***

<div className="w-72 border-r border-white/10 backdrop-blur-xl bg-white/[0.03***REMOVED*** p-5">

<div className="space-y-2">

{[
["Memory",Database***REMOVED***,
["Knowledge",Brain***REMOVED***,
["Agents",Bot***REMOVED***,
["Bridge",Network***REMOVED***,
["Projects",FolderTree***REMOVED***,
["Events",Activity***REMOVED***,
["Planner",Cpu***REMOVED***,
["Graph",GitBranch***REMOVED***,
***REMOVED***.map(([label,Icon***REMOVED***)=>(

<button
key={label***REMOVED***
className="w-full rounded-2xl px-4 py-3 flex items-center gap-3 hover:bg-white/5 transition"
>

<Icon size={18***REMOVED***/>

<span>{label***REMOVED***</span>

</button>

))***REMOVED***

</div>

<div className="mt-10">

<div className="text-xs uppercase tracking-widest text-slate-500 mb-3">
System
</div>

<div className="rounded-2xl bg-gradient-to-br from-cyan-500/20 to-blue-500/10 border border-cyan-400/20 p-4">

<div className="text-sm text-cyan-200">
Orchestrator
</div>

<div className="mt-2 text-3xl font-semibold">
Healthy
</div>

<div className="mt-3 h-2 rounded-full bg-white/10 overflow-hidden">

<div className="h-full w-[92%***REMOVED*** bg-cyan-400 rounded-full"/>

</div>

</div>

</div>

</div>

{/* CENTER */***REMOVED***

<div className="flex-1 relative">

<svg className="absolute inset-0 w-full h-full">

{edges.map(([a,b***REMOVED***,i)=>{

const n1=lookup[a***REMOVED***;
const n2=lookup[b***REMOVED***;

return(

<line
key={i***REMOVED***
x1={`${n1.x***REMOVED***%`***REMOVED***
y1={`${n1.y***REMOVED***%`***REMOVED***
x2={`${n2.x***REMOVED***%`***REMOVED***
y2={`${n2.y***REMOVED***%`***REMOVED***
stroke="rgba(118,170,255,.35)"
strokeWidth="2"
/>

)

***REMOVED***)***REMOVED***

</svg>

{nodes.map(node=>(

<div

key={node.id***REMOVED***

onClick={()=>setSelected(node)***REMOVED***

className="absolute -translate-x-1/2 -translate-y-1/2 cursor-pointer"

style={{
left:`${node.x***REMOVED***%`,
top:`${node.y***REMOVED***%`
***REMOVED******REMOVED***

>

<div
className="rounded-full animate-pulse"
style={{
width:node.size*3,
height:node.size*3,
background:`radial-gradient(circle, ${node.color***REMOVED***, transparent)`
***REMOVED******REMOVED***
/>

<div
className="absolute inset-0 rounded-full border"
style={{
borderColor:node.color
***REMOVED******REMOVED***
/>

<div className="mt-2 text-center text-xs whitespace-nowrap">
{node.label***REMOVED***
</div>

</div>

))***REMOVED***

</div>

{/* RIGHT */***REMOVED***

<div className="w-80 border-l border-white/10 bg-white/[0.03***REMOVED*** backdrop-blur-xl p-6">

<div className="flex items-center gap-2">

<Sparkles className="text-cyan-300"/>

<h2 className="font-semibold">
{selected.label***REMOVED***
</h2>

</div>

<div className="mt-6 rounded-2xl bg-white/5 border border-white/10 p-5">

<div className="text-slate-400 text-sm">
Status
</div>

<div className="mt-2 text-xl">
Running
</div>

<div className="mt-6 grid gap-3">

{[
["Connections","12"***REMOVED***,
["Latency","14 ms"***REMOVED***,
["Tasks","7"***REMOVED***,
["Health","98%"***REMOVED***,
***REMOVED***.map(([k,v***REMOVED***)=>(

<div
key={k***REMOVED***
className="flex justify-between text-sm"
>

<span className="text-slate-400">{k***REMOVED***</span>

<span>{v***REMOVED***</span>

</div>

))***REMOVED***

</div>

</div>

<div className="mt-6">

<div className="text-sm text-slate-400 mb-3">
Recent Events
</div>

<div className="space-y-3">

{[
"Knowledge indexed",
"Hermes connected",
"Task routed",
"Memory checkpoint",
***REMOVED***.map(event=>(

<div
key={event***REMOVED***
className="rounded-xl bg-white/5 border border-white/10 px-4 py-3 text-sm"
>

{event***REMOVED***

</div>

))***REMOVED***

</div>

</div>

</div>

</div>

</div>

);

***REMOVED***