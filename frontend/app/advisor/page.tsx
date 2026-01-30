"use client";

import { useState, useRef, useEffect } from 'react';
import Image from 'next/image';
import styles from './page.module.css';
import { API } from '../../lib/api';
import { authFetch } from '../../lib/auth';
import { useAuthGuard } from '../../lib/useAuthGuard';
import TryOnVisualizer from '../../components/TryOnVisualizer';
import { WalletConfirmationModal } from '../../components/WalletConfirmationModal';
import advisorImage from '../images/shopping_advisor.png';

export default function AdvisorPage() {
    useAuthGuard();
    const [file, setFile] = useState<File | null>(null);
    const [preview, setPreview] = useState<string | null>(null);
    const [status, setStatus] = useState<'idle' | 'analyzing' | 'chatting'>('chatting');
    const [messages, setMessages] = useState<any[]>([]);
    const [input, setInput] = useState('');
    const [analysisData, setAnalysisData] = useState<any>(null);
    const [userPhoto, setUserPhoto] = useState<string | null>(null);
    const [user, setUser] = useState<any>(null);
    const [tryOnData, setTryOnData] = useState<any>(null);
    const [showIntro, setShowIntro] = useState(true);

    const [walletModalData, setWalletModalData] = useState<{
        isOpen: boolean;
        itemName: string;
        price: number;
        currency: string;
        balance: number;
    }>({
        isOpen: false,
        itemName: '',
        price: 0,
        currency: 'TND',
        balance: 0
    });

    const messagesEndRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    useEffect(() => {
        const timer = setTimeout(() => setShowIntro(false), 2200);
        return () => clearTimeout(timer);
    }, []);

    useEffect(() => {
        const fetchUser = async () => {
            try {
                const res = await authFetch(API.users.me);
                if (res.ok) {
                    const data = await res.json();
                    setUser(data);
                    setUserPhoto(data.full_body_image);
                }
            } catch (err) { console.error(err); }
        };
        fetchUser();
    }, []);

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            const selected = e.target.files[0];
            setFile(selected);
            setPreview(URL.createObjectURL(selected));
            setAnalysisData(null);
        }
    };

    const handleSend = async () => {
        const text = input.trim();
        const currentFile = file;
        const currentPreview = preview;

        if (!text && !currentFile) return;

        setInput('');

        if (status === 'chatting') {
            setMessages(prev => [
                ...prev,
                { role: 'user', text, image: currentFile ? currentPreview : null }
            ]);
        }

        if (currentFile && !analysisData) {
            // Analyze first to get the matches/metadata for the UI & context
            setStatus('analyzing');
            const formData = new FormData();
            formData.append('file', currentFile);
            try {
                const res = await authFetch(API.stylist.advisor, { method: 'POST', body: formData });
                if (res.ok) {
                    const data = await res.json();
                    setAnalysisData(data);
                    const targetInfo = data.target_analysis || {};
                    const matchCount = data.matches?.length || 0;

                    // Enriched request context
                    const enrichedText = text
                        ? `${text} (Context: This is a ${targetInfo.sub_category || 'item'} with ${matchCount} closet matches)`
                        : `Evaluate this ${targetInfo.sub_category || 'item'}. It has ${matchCount} closet matches.`;

                    setStatus('chatting');
                    await sendToAI(enrichedText, currentFile, currentPreview, false);
                } else {
                    setStatus('chatting');
                    await sendToAI(text || "Evaluate this potential purchase.", currentFile, currentPreview, false);
                }
            } catch (err) {
                setStatus('chatting');
                await sendToAI(text || "Evaluate this potential purchase.", currentFile, currentPreview, false);
            }
        } else {
            await sendToAI(text, currentFile, currentPreview, false);
        }

        // Clear file state after sending
        if (currentFile) {
            setFile(null);
            // We keep the preview ONLY if we have analysisData (to show the sticky panel)
            // But actually preview is used for the sticky panel. 
            // If we setFile(null), handleFileChange works again next time.
        }
    };

    const sendToAI = async (
        text: string,
        currentFile?: File | null,
        currentPreview?: string | null,
        appendUserMessage: boolean = true
    ) => {
        if (!text.trim() && !currentFile) return;
        if (status === 'chatting' && appendUserMessage) {
            setMessages(prev => [...prev, { role: 'user', text, image: currentFile ? currentPreview : null }]);
        }

        const formData = new FormData();

        let enrichedText = text;
        if (analysisData && !currentFile && !text.includes("[Context")) {
            const item = analysisData.target_analysis?.sub_category || "this item";
            enrichedText = `[Context: Regarding the potential ${item}] ${text}`;
        }

        formData.append('message', enrichedText);
        if (currentFile) formData.append('file', currentFile);

        // Filter out incomplete/status messages
        const history = messages
            .filter(m => m.text && m.text.length > 0)
            .map(m => ({ role: m.role, content: m.text }));

        formData.append('history', JSON.stringify(history));

        try {
            const res = await authFetch(API.stylist.chat, { method: 'POST', body: formData });
            if (res.ok && res.body) {
                const reader = res.body.getReader();
                const decoder = new TextDecoder();
                let buffer = '';
                setMessages(prev => [...prev, { role: 'assistant', text: '', status: 'Routing your request...' }]);

                while (true) {
                    const { value, done } = await reader.read();
                    if (done) break;
                    buffer += decoder.decode(value, { stream: true });
                    const lines = buffer.split('\n\n');
                    buffer = lines.pop() || '';

                    for (const line of lines) {
                        if (line.startsWith('data: ')) {
                            try {
                                const event = JSON.parse(line.slice(6));
                                if (event.type === 'status') {
                                    setMessages(prev => {
                                        const next = [...prev];
                                        next[next.length - 1].status = event.content;
                                        return next;
                                    });
                                } else if (event.type === 'chunk') {
                                    setMessages(prev => {
                                        const next = [...prev];
                                        const last = next[next.length - 1];
                                        last.text = (last.text || '') + event.content;
                                        return next;
                                    });
                                } else if (event.type === 'final') {
                                    const botResponse = event.content;
                                    setMessages(prev => {
                                        const next = [...prev];
                                        next[next.length - 1] = {
                                            role: 'assistant',
                                            text: botResponse.response,
                                            images: botResponse.images,
                                            suggested_outfits: botResponse.suggested_outfits,
                                            status: undefined
                                        };
                                        return next;
                                    });

                                    if (botResponse.wallet_confirmation?.required) {
                                        const wc = botResponse.wallet_confirmation;
                                        setWalletModalData({
                                            isOpen: true,
                                            itemName: wc.item_name,
                                            price: wc.price,
                                            currency: wc.currency,
                                            balance: user?.wallet_balance || wc.current_balance
                                        });
                                    }
                                }
                            } catch (e) { }
                        }
                    }
                }
            }
        } catch (err) {
            setMessages(prev => [...prev, { role: 'assistant', text: "Error connecting to stylist server." }]);
        }
    };

    const handlePurchaseSuccess = async (newBalance: number) => {
        setUser((prev: any) => ({ ...prev, wallet_balance: newBalance }));
        setMessages(prev => [...prev, { role: 'assistant', text: `Confirmed! Deducted **${walletModalData.price} ${walletModalData.currency}**. Item added to closet.` }]);
        if (file) {
            const formData = new FormData();
            formData.append('file', file);
            formData.append('price', walletModalData.price.toString());
            await authFetch(API.clothing.ingest, { method: 'POST', body: formData });
        }
    };

    const renderMarkdown = (content: string) => {
        if (!content) return null;
        const imageRegex = /!\[([^\]]*)\]\(([^)]+)\)/g;
        const boldRegex = /\*\*([^*]+)\*\*/g;
        let parts: (string | React.ReactNode)[] = [content];

        parts = parts.flatMap((part): (string | React.ReactNode)[] => {
            if (typeof part !== 'string') return [part];
            return part.split(boldRegex).map((bit, i): string | React.ReactNode => i % 2 === 1 ? <strong key={i}>{bit}</strong> : bit);
        });

        parts = parts.flatMap((part): (string | React.ReactNode)[] => {
            if (typeof part !== 'string') return [part];
            const bits = part.split(imageRegex);
            const elements: (string | React.ReactNode)[] = [];
            for (let i = 0; i < bits.length; i += 3) {
                elements.push(bits[i] as string);
                if (bits[i + 1] !== undefined) {
                    elements.push(<img key={i} src={bits[i + 2]} alt={bits[i + 1]} className={styles.renderedImage} />);
                }
            }
            return elements;
        });
        return parts;
    };

    return (
        <div className={styles.container}>
            {showIntro && (
                <div className={styles.introOverlay} aria-hidden="true">
                    <Image
                        src={advisorImage}
                        alt=""
                        className={styles.introCart}
                        priority
                    />
                </div>
            )}
            <header className={styles.header}>
                <div>
                    <h1>Shopping Advisor</h1>
                    <p>Get instant feedback on potential purchases.</p>
                </div>
                {user && (
                    <div className={styles.budgetCard}>
                        <span className={styles.budgetLabel}>My Budget</span>
                        <div className={styles.budgetValue}>
                            {user.wallet_balance.toLocaleString()} {user.currency || 'TND'}
                        </div>
                    </div>
                )}
            </header>

            <div className={styles.chatContainer}>
                <div className={styles.chatMain}>
                    {preview && (
                        <div className={styles.insightPanel}>
                            <img src={preview!} className={styles.insightThumb} />
                            <div className={styles.insightStats}>
                                <div>
                                    <small>Item</small>
                                    <div><strong>{analysisData?.target_analysis?.sub_category || "Detected"}</strong></div>
                                </div>
                                <div>
                                    <small>Similarity</small>
                                    <div><strong>{analysisData?.matches?.[0] ? Math.round(analysisData.matches[0].score * 100) : 0}%</strong></div>
                                </div>
                                {analysisData?.matches && (
                                    <div>
                                        <small>Closet Matches</small>
                                        <div className={styles.matchMiniList}>
                                            {analysisData.matches.slice(0, 3).map((m: any, idx: number) => (
                                                <img key={idx} src={m.image_url} className={styles.matchMiniImg} />
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </div>
                            <button className={styles.closeInsight} onClick={() => { setPreview(null); setFile(null); setAnalysisData(null); }}>×</button>
                        </div>
                    )}

                    <div className={styles.chatMessages}>
                        {messages.length === 0 && (
                            <div className={styles.welcomeTip}>
                                <div className={styles.tipIcon}>💡</div>
                                <h3>I'm your FinCommerce Advisor</h3>
                                <p>Ask me about trends, your budget, or upload a "Potential Buy" to see how it fits your closet and wallet.</p>
                            </div>
                        )}
                        {messages.map((msg, i) => (
                            <div key={i} className={`${styles.message} ${styles[msg.role]}`}>
                                <div className={styles.bubble}>
                                    {msg.image && (
                                        <div className={styles.messageMedia}>
                                            <img
                                                src={msg.image}
                                                alt="uploaded"
                                                className={styles.messageImage}
                                                onClick={() => window.open(msg.image, '_blank')}
                                            />
                                        </div>
                                    )}
                                    <div className={styles.textContent}>{renderMarkdown(msg.text)}</div>
                                    {msg.status && (
                                        <div className={styles.streamingStatus}>
                                            <span className={styles.statusLabel}>Active agent:</span>
                                            <span>{msg.status}</span>
                                            {!msg.text && (
                                                <span className={styles.typingDots} aria-label="Assistant is typing">
                                                    <span />
                                                    <span />
                                                    <span />
                                                </span>
                                            )}
                                        </div>
                                    )}
                                    {msg.images && Array.isArray(msg.images) && msg.images.length > 0 && (
                                        <div className={styles.messageMedia}>
                                            {msg.images.map((img: string, idx: number) => (
                                                <img
                                                    key={idx}
                                                    src={img}
                                                    alt="assistant"
                                                    className={styles.messageImage}
                                                    onClick={() => window.open(img, '_blank')}
                                                />
                                            ))}
                                        </div>
                                    )}
                                    {msg.suggested_outfits && (
                                        <div className={styles.outfitStack}>
                                            {msg.suggested_outfits.map((fit: any, idx: number) => (
                                                <button
                                                    key={idx}
                                                    className={styles.fitBadge}
                                                    onClick={async () => {
                                                        if (!userPhoto || !fit.item_details) return;

                                                        // Set immediate status
                                                        setMessages(prev => {
                                                            const next = [...prev];
                                                            const last = next[next.length - 1];
                                                            last.status = "Glam is sketching your virtual try-on... ✨ (60-80s)";
                                                            return next;
                                                        });

                                                        try {
                                                            // Prepare items for backend
                                                            const itemsForBackend = fit.item_details.map((item: any) => {
                                                                // Use the cloud-stored URL for potential purchase (if available)
                                                                let url = item.image_url;
                                                                if (item.id === 'potential_purchase') {
                                                                    url = analysisData?.image_url || preview;
                                                                }
                                                                return {
                                                                    id: item.id,
                                                                    image_url: url,
                                                                    body_region: item.body_region || 'top'
                                                                };
                                                            });

                                                            const res = await authFetch(API.stylist.tryon, {
                                                                method: 'POST',
                                                                headers: { 'Content-Type': 'application/json' },
                                                                body: JSON.stringify({ items: itemsForBackend })
                                                            });

                                                            if (res.ok) {
                                                                const data = await res.json();
                                                                setTryOnData({
                                                                    items: itemsForBackend,
                                                                    tryonImageUrl: data.url,
                                                                    name: fit.name
                                                                });
                                                            } else {
                                                                // Fallback to layering
                                                                setTryOnData({ items: itemsForBackend, tryonImageUrl: undefined });
                                                            }
                                                        } catch (err) {
                                                            console.error("Tryon error:", err);
                                                        } finally {
                                                            setMessages(prev => {
                                                                const next = [...prev];
                                                                next[next.length - 1].status = undefined;
                                                                return next;
                                                            });
                                                        }
                                                    }}
                                                >
                                                    ✨ {fit.name} ({fit.score}/10)
                                                </button>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            </div>
                        ))}
                        <div ref={messagesEndRef} />
                    </div>

                    {status === 'analyzing' && (
                        <div className={styles.inlineAnalyzing}>
                            <div className={styles.analyzeIcon}>🧪</div>
                            <div className={styles.analyzeContent}>
                                <div className={styles.analyzeTitle}>
                                    Analyzing your potential buy
                                    <span className={styles.loadingDots} aria-hidden="true">
                                        <span />
                                        <span />
                                        <span />
                                    </span>
                                </div>
                                <div className={styles.analyzeSteps}>
                                    <span>Visual match</span>
                                    <span>Closet check</span>
                                    <span>Style & budget fit</span>
                                </div>
                                <div className={styles.analyzeBar}>
                                    <span />
                                </div>
                            </div>
                        </div>
                    )}
                    <div className={styles.chatInputArea}>
                        <label className={styles.uploadIconButton} title="Upload Potential Buy">
                            <input type="file" accept="image/*" onChange={(e) => handleFileChange(e)} hidden />
                            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="17 8 12 3 7 8" /><line x1="12" y1="3" x2="12" y2="15" /></svg>
                        </label>

                        {file && !analysisData && (
                            <div className={styles.pendingAttachment}>
                                <img src={preview!} alt="attached" />
                                <button onClick={() => { setFile(null); setPreview(null); }} className={styles.removePending}>×</button>
                            </div>
                        )}

                        <div className={styles.inputWrapper}>
                            <input
                                placeholder={file ? "Add info (e.g. 'Costs 50 TND')..." : "Message advisor (e.g. 'What can I afford?')..."}
                                value={input}
                                onChange={(e) => setInput(e.target.value)}
                                onKeyPress={(e) => e.key === 'Enter' && handleSend()}
                            />
                        </div>
                        <button onClick={handleSend} className={styles.sendBtn}>
                            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><line x1="22" y1="2" x2="11" y2="13" /><polygon points="22 2 15 22 11 13 2 9 22 2" /></svg>
                        </button>
                    </div>
                </div>
            </div>

            {tryOnData && userPhoto && <TryOnVisualizer bodyImage={userPhoto} items={tryOnData.items} tryonImageUrl={tryOnData.tryonImageUrl} onClose={() => setTryOnData(null)} />}
            <WalletConfirmationModal {...walletModalData} onClose={() => setWalletModalData(prev => ({ ...prev, isOpen: false }))} onSuccess={handlePurchaseSuccess} />
        </div>
    );
}
