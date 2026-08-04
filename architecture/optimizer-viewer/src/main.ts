import './style.css'

import {createIcons, Download, Focus, GitBranch, Info, Menu, Minus, Plus, X,} from 'lucide'
import mermaid from 'mermaid'
import svgPanZoom, {type SvgPanZoomInstance} from 'svg-pan-zoom'

import {diagrams, type DiagramSpec, type NodeDetail} from './diagrams'

mermaid.initialize({
  startOnLoad: false,
  securityLevel: 'loose',
  theme: 'base',
  flowchart:
      {curve: 'basis', htmlLabels: true, nodeSpacing: 36, rankSpacing: 64},
  sequence: {useMaxWidth: false, actorMargin: 48, messageMargin: 34},
  class: {useMaxWidth: false},
  themeVariables: {
    background: '#f7f6f1',
    primaryColor: '#edf2f0',
    primaryTextColor: '#1c2928',
    primaryBorderColor: '#416561',
    lineColor: '#61706d',
    secondaryColor: '#fff1dc',
    tertiaryColor: '#eef1f4',
    fontFamily: 'Avenir Next, Trebuchet MS, sans-serif',
    fontSize: '15px',
    noteBkgColor: '#fff7e9',
    noteBorderColor: '#c56b20',
    actorBkg: '#edf2f0',
    actorBorder: '#416561',
    actorTextColor: '#1c2928',
    signalColor: '#465e5a',
    signalTextColor: '#263735',
  },
})

const app = document
                .querySelector<HTMLDivElement>('#app')!

            app.innerHTML = `
  <div class="shell">
    <aside class="sidebar" id="sidebar">
      <div class="brand">
        <div class="brand-mark"><i data-lucide="git-branch"></i></div>
        <div>
          <span class="eyebrow">Architecture</span>
          <strong>EPS optimizer</strong>
        </div>
        <button class="icon-button sidebar-close" id="sidebar-close" aria-label="Close navigation" title="Close navigation">
          <i data-lucide="x"></i>
        </button>
      </div>

      <nav class="view-nav" aria-label="Architecture views">
        <p class="nav-label">Views</p>
        ${
    diagrams
        .map(
            (diagram, index) => `
            <button class="view-button${
                index === 0 ? ' active' : ''}" data-diagram="${diagram.id}">
              <span>${diagram.number}</span>
              <span class="view-name">${diagram.shortTitle}<small>${
                diagram.kind}</small></span>
            </button>`,
            )
        .join('')}
      </nav>

    </aside>

    <main class="workspace">
      <header class="topbar">
        <button class="icon-button menu-button" id="menu-button" aria-label="Open navigation" title="Open navigation">
          <i data-lucide="menu"></i>
        </button>
        <div class="breadcrumb">Optimizer architecture</div>
        <div class="top-actions">
          <button class="command-button primary" id="export-button" aria-label="Export diagram as SVG" title="Export diagram as SVG"><i data-lucide="download"></i><span>Export SVG</span></button>
        </div>
      </header>

      <section class="content">
        <div class="diagram-heading">
          <div>
            <span class="kind-badge" id="diagram-kind">Component</span>
            <h1 id="diagram-title"></h1>
            <p id="diagram-description"></p>
          </div>
        </div>

        <div class="canvas-frame">
          <div class="canvas-toolbar" aria-label="Diagram controls">
            <button class="icon-button" id="zoom-in" aria-label="Zoom in" title="Zoom in"><i data-lucide="plus"></i></button>
            <button class="icon-button" id="zoom-out" aria-label="Zoom out" title="Zoom out"><i data-lucide="minus"></i></button>
            <span></span>
            <button class="icon-button" id="fit-view" aria-label="Fit diagram" title="Fit diagram"><i data-lucide="focus"></i></button>
          </div>
          <div class="diagram-stage" id="diagram-stage">
            <div class="loading-state"><span></span><p>Compiling diagram source</p></div>
          </div>
          <div class="canvas-caption">
            <span><i data-lucide="info"></i> Select an element for implementation details.</span>
          </div>
        </div>
      </section>
    </main>

    <aside class="inspector" id="inspector" aria-live="polite">
      <div class="inspector-head">
        <span>Element inspector</span>
        <button class="icon-button" id="inspector-close" aria-label="Close inspector" title="Close inspector"><i data-lucide="x"></i></button>
      </div>
      <div class="inspector-body" id="inspector-body">
        <div class="empty-inspector">
          <i data-lucide="info"></i>
          <h2>Nothing selected</h2>
          <p>Select a node or participant in the diagram to see its implementation role and guarantee.</p>
        </div>
      </div>
    </aside>
  </div>

`

createIcons({
  icons: {
    Download,
    Focus,
    GitBranch,
    Info,
    Menu,
    Minus,
    Plus,
    X,
  },
})

const stage = document.querySelector<HTMLDivElement>('#diagram-stage')!;
const inspector = document.querySelector<HTMLElement>('#inspector')!;
const inspectorBody =
    document.querySelector<HTMLDivElement>('#inspector-body')!;
let activeDiagram = diagrams[0];
let panZoom: SvgPanZoomInstance|null = null;
let renderSequence = 0;

function showInspector(detail: NodeDetail): void{inspector.classList.add('open')
      inspectorBody.innerHTML = `
    <div class="detail-type">${detail.type}</div>
    <h2>${detail.title}</h2>
    <p>${detail.body}</p>
    <dl>
      <div><dt>Implementation</dt><dd>${detail.source}</dd></div>
      <div><dt>Guarantee</dt><dd>${detail.guarantee}</dd></div>
    </dl>
  `
    }

function attachInspection(diagram: DiagramSpec):
    void {
  const candidates =
      stage.querySelectorAll<SVGGElement>('g.node, g.classGroup, g.actor')
  candidates.forEach((element) => {
    const text = element.textContent?.replace(/\s+/g, ' ').trim() ?? ''
    const detail = diagram.details.find((item) => text.includes(item.match))
    if (!detail) {
      return;
    }
    element.classList.add('inspectable')
    element.setAttribute('tabindex', '0')
    element.setAttribute('role', 'button')
    element.setAttribute('aria-label', `Inspect ${detail.title}`)
    element.addEventListener('click', () => showInspector(detail))
    element.addEventListener('keydown', (event) => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault()
        showInspector(detail)
      }
    })
  })
    }

async function renderDiagram(diagram: DiagramSpec):
    Promise<void> {
  const sequence = ++renderSequence
  activeDiagram = diagram
  document.querySelector('#diagram-kind')!.textContent = diagram.kind
  document.querySelector('#diagram-title')!.textContent = diagram.title
  document.querySelector('#diagram-description')!.textContent =
      diagram.description
  document.querySelectorAll<HTMLButtonElement>('.view-button')
      .forEach(
          (button) => {button.classList.toggle(
              'active', button.dataset.diagram === diagram.id)})

  panZoom?.destroy()
  panZoom = null
  stage.innerHTML =
      '<div class="loading-state"><span></span><p>Compiling diagram source</p></div>'

  try {
    const {svg} = await mermaid.render(
        `optimizer-${diagram.id}-${sequence}`, diagram.source)
    if (sequence !== renderSequence) {
      return;
    }
    stage.innerHTML = svg;
    const svgElement = stage.querySelector<SVGSVGElement>('svg')!
                       svgElement.removeAttribute('height')
    svgElement.removeAttribute('width')
    svgElement.setAttribute('preserveAspectRatio', 'xMidYMid meet')
    svgElement.style.width = '100%'
    svgElement.style.height = '100%'
    attachInspection(diagram)
    panZoom = svgPanZoom(svgElement, {
      controlIconsEnabled: false,
      fit: true,
      center: true,
      minZoom: 0.25,
      maxZoom: 8,
      zoomScaleSensitivity: 0.24,
      dblClickZoomEnabled: true,
    })
    requestAnimationFrame(() => {
      panZoom?.resize()
    panZoom?.fit()
      panZoom?.center()
    })
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error)
    stage.innerHTML =
        `<div class="error-state"><strong>Diagram could not be compiled</strong><p>${
            message}</p></div>`
  }
    }

function exportSvg():
    void {
  const svg = stage.querySelector<SVGSVGElement>('svg')
  if (!svg) {
    return;
  }
  const clone = svg.cloneNode(true) as SVGSVGElement;
  clone.setAttribute('xmlns', 'http://www.w3.org/2000/svg')
  const blob =
      new Blob([clone.outerHTML], {type: 'image/svg+xml;charset=utf-8'})
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = `optimizer-${activeDiagram.id}.svg`
  link.click()
  URL.revokeObjectURL(link.href)
    }

document.querySelectorAll<HTMLButtonElement>('.view-button')
    .forEach(
        (button) => {button.addEventListener('click', () => {
  const next = diagrams.find((diagram) => diagram.id === button.dataset.diagram)
  if (next) void renderDiagram(next)
  document.querySelector('#sidebar')?.classList.remove('mobile-open')
        })})

      document.querySelector('#zoom-in')
          ?.addEventListener('click', () => panZoom?.zoomIn())
      document.querySelector('#zoom-out')
          ?.addEventListener('click', () => panZoom?.zoomOut())
document.querySelector('#fit-view')?.addEventListener('click', () => {
  panZoom?.fit()
  panZoom?.center()
})
  document.querySelector('#export-button')?.addEventListener('click', exportSvg)
  document.querySelector('#inspector-close')
      ?.addEventListener('click', () => inspector.classList.remove('open'))
  document.querySelector('#menu-button')
      ?.addEventListener(
          'click',
          () =>
              document.querySelector('#sidebar')?.classList.add('mobile-open'))
  document.querySelector('#sidebar-close')
      ?.addEventListener(
          'click',
          () => document.querySelector('#sidebar')
                    ?.classList.remove('mobile-open'))

          void renderDiagram(activeDiagram)