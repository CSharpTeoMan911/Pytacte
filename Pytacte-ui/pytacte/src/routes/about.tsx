import { useEffect, useRef, useState } from 'react'
import { createFileRoute } from '@tanstack/react-router'
import { GlobalWorkerOptions, getDocument } from 'pdfjs-dist'
import type { PDFDocumentProxy, RenderTask } from 'pdfjs-dist'
import CustomAppBar from '#/components/CustomAppBar'
import DeviceSelector from '#/components/DeviceSelector'
import RootPanel from '#/components/RootPanel'
import aboutPdf from '../data/About.pdf'
import pdfWorkerUrl from 'pdfjs-dist/build/pdf.worker.min.mjs?url'

GlobalWorkerOptions.workerSrc = pdfWorkerUrl

export const Route = createFileRoute('/about')({
    component: RouteComponent,
})

function RouteComponent() {
    const pdfPagesRef = useRef<HTMLDivElement>(null)
    const pageCanvasRefs = useRef<Array<HTMLCanvasElement | null>>([])
    const [pdfDocument, setPdfDocument] = useState<PDFDocumentProxy | null>(null)
    const [pdfContainerWidth, setPdfContainerWidth] = useState(0)
    const [pdfLoadError, setPdfLoadError] = useState(false)

    useEffect(() => {
        const loadingTask = getDocument({ url: aboutPdf })
        let cancelled = false

        loadingTask.promise
            .then((document) => {
                if (!cancelled) setPdfDocument(document)
            })
            .catch((error: unknown) => {
                console.error('Unable to load About.pdf:', error)
                if (!cancelled) setPdfLoadError(true)
            })

        return () => {
            cancelled = true
            void loadingTask.destroy()
        }
    }, [])

    useEffect(() => {
        const container = pdfPagesRef.current
        if (!container) return

        const resizeObserver = new ResizeObserver(([entry]) => {
            setPdfContainerWidth(entry.contentRect.width)
        })
        resizeObserver.observe(container)
        return () => resizeObserver.disconnect()
    }, [])

    useEffect(() => {
        if (!pdfDocument || pdfContainerWidth <= 0) return;

        let cancelled = false;
        const renderTasks: RenderTask[] = [];

        async function renderPages() {
            if (!pdfDocument) return;
            for (let pageNumber = 1; pageNumber <= pdfDocument.numPages; pageNumber += 1) {
                const canvas = pageCanvasRefs.current[pageNumber - 1]
                if (!canvas) continue

                const page = await pdfDocument.getPage(pageNumber)
                if (cancelled) return

                const baseViewport = page.getViewport({ scale: 1 })
                const scale = pdfContainerWidth / baseViewport.width / 2
                const viewport = page.getViewport({ scale })
                const pixelRatio = window.devicePixelRatio || 1
                const context = canvas.getContext('2d')
                if (!context) continue

                canvas.width = Math.floor(viewport.width * pixelRatio)
                canvas.height = Math.floor(viewport.height * pixelRatio)
                canvas.style.width = `${viewport.width}px`
                canvas.style.height = `${viewport.height}px`

                const renderTask = page.render({
                    canvas,
                    canvasContext: context,
                    viewport,
                    transform: pixelRatio === 1 ? undefined : [pixelRatio, 0, 0, pixelRatio, 0, 0],
                })
                renderTasks.push(renderTask)
                await renderTask.promise
                if (cancelled) return
            }
        }

        renderPages().catch((error: unknown) => {
            if (!cancelled) console.error('Unable to render About.pdf:', error)
        })

        return () => {
            cancelled = true
            renderTasks.forEach((task) => task.cancel())
        }
    }, [pdfDocument, pdfContainerWidth])

    const pdfContent = pdfLoadError ? (
        <p role='alert' style={{ color: '#fff', textAlign: 'center' }}>Unable to display the About PDF.</p>
    ) : pdfDocument ? (
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '16px' }}>
            {Array.from({ length: pdfDocument.numPages }, (_, index) => (
                <canvas
                    key={index + 1}
                    ref={(canvas) => { pageCanvasRefs.current[index] = canvas }}
                    aria-label={`About PDF page ${index + 1}`}
                    style={{ display: 'block', maxWidth: '100%', backgroundColor: '#fff' }}
                />
            ))}
        </div>
    ) : (
        <p style={{ color: '#fff', textAlign: 'center' }}>Loading document…</p>
    )

    const pdfPages = (className?: string) => (
        <div id='about-pdf-pages' className={className} ref={pdfPagesRef} aria-label='About PDF pages' style={{ width: '100%', height: 'calc(100vh - 64px)', overflowY: 'auto', margin: 0, padding: 0, boxSizing: 'border-box' }}>
            {pdfContent}
        </div>
    )

    return (
        <RootPanel style={{ background: '#fff', display: 'flex', flexDirection: 'column', height:'100vh' }}>
            <style>
                @import url('https://fonts.googleapis.com/css2?family=Roboto+Mono:ital,wght@0,100..700;1,100..700&display=swap');
                @import url('https://fonts.googleapis.com/css2?family=Micro+5&family=Tiny5+Duo:ital,wght@0,100..900;1,100..900&display=swap');
            </style>
            <style>{`
                #about-pdf-pages {
                    scrollbar-width: thin;
                    scrollbar-color: #003b5f #fff;
                }
                #about-pdf-pages::-webkit-scrollbar {
                    width: 6px;
                }
                #about-pdf-pages::-webkit-scrollbar-track {
                    background: #fff;
                }
                #about-pdf-pages::-webkit-scrollbar-thumb {
                    background: #003b5f;
                    border-radius: 6px;
                }
                #about-pdf-pages:focus,
                #about-pdf-pages:focus-visible,
                #about-pdf-pages:active,
                #about-pdf-pages canvas:focus,
                #about-pdf-pages canvas:focus-visible,
                #about-pdf-pages canvas:active {
                    outline: none;
                    box-shadow: none;
                }
            `}</style>
            <DeviceSelector
                desktopChildren={null}
                mobileChildren={
                    <style>{`
                        #about-pdf-pages {
                            scrollbar-width: none;
                            -ms-overflow-style: none;
                        }
                        #about-pdf-pages::-webkit-scrollbar {
                            display: none;
                        }
                    `}</style>
                }
            />

            <CustomAppBar
                logoWidth="50px"
                logoHeight="50px"
                appBarTextColor="#003b5f"
                appBarColor="#f8f8f8"
                appBarSecondaryTextColor="#0a70ac"
                authButtonTextColor="#003b5f"
                routesInfo={[
                    ['/', 'Transcription'],
                    ['/about', 'About'],
                    ['/auth', '[auth]'],
                ]}
            />

            <div id='about-pdf-pages' ref={pdfPagesRef} aria-label='About PDF pages' style={{ width: '100%', height: '100vh', overflowY: 'auto', margin: 0, padding: 0, boxSizing: 'border-box' }}>
                {pdfLoadError ? (
                    <p role='alert' style={{ color: '#fff', textAlign: 'center' }}>Unable to display the About PDF.</p>
                ) : pdfDocument ? (
                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '16px' }}>
                        {Array.from({ length: pdfDocument.numPages }, (_, index) => (
                            <canvas
                                key={index + 1}
                                ref={(canvas) => { pageCanvasRefs.current[index] = canvas }}
                                aria-label={`About PDF page ${index + 1}`}
                                style={{ display: 'block', maxWidth: '100%', backgroundColor: '#fff' }}
                            />
                        ))}
                    </div>
                ) : (
                    <p style={{ color: '#fff', textAlign: 'center' }}>Loading document…</p>
                )}
            </div>
        </RootPanel>
    )
}
