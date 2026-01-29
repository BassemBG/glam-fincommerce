"use client";

import { useState, useRef, useEffect } from 'react';
import styles from './page.module.css';
import { API } from '../../lib/api';
import { authFetch } from '../../lib/auth';
import { useAuthGuard } from '../../lib/useAuthGuard';
import TryOnVisualizer from '../../components/TryOnVisualizer';
import { WalletConfirmationModal } from '../../components/WalletConfirmationModal';

export default function AdvisorPage() {
    useAuthGuard();
    const [file, setFile] = useState<File | null>(null);
    const [preview, setPreview] = useState<string | null>(null);
    const [status, setStatus] = useState<'idle' | 'analyzing' | 'chatting'>('idle');
    const [messages, setMessages] = useState<any[]>([]);
    const [input, setInput] = useState('');
    const [analysisData, setAnalysisData] = useState<any>(null);
    const [userPhoto, setUserPhoto] = useState<string | null>(null);
    const [user, setUser] = useState<any>(null);
    const [tryOnData, setTryOnData] = useState<any>(null);

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
            setStatus('idle');
            setAnalysisData(null);
        }
    };

    const startAnalysis = async () => {
        if (!file) return;
        setStatus('analyzing');

        const formData = new FormData();
        formData.append('file', file);

        try {
            const res = await authFetch(API.stylist.advisor, { method: 'POST', body: formData });
            if (res.ok) {
                const data = await res.json();
                setAnalysisData(data);
                const targetInfo = data.target_analysis || {};
                const matchCount = data.matches?.length || 0;
                const req = `I'm considering buying this ${targetInfo.sub_category || targetInfo.category || 'item'}. It has colors like ${targetInfo.colors?.join(', ') || 'unknown'}. Can you evaluate it against my closet? I have ${matchCount} similar items already. (Glam, please transfer this to the Fashion Advisor).`;

                setStatus('chatting');
                await sendToAI(req, file);
            } else {
                alert("Analysis failed.");
                setStatus('idle');
            }
        } catch (err) {
            console.error(err);
            setStatus('idle');
        }
    };

    const sendToAI = async (text: string, currentFile?: File | null) => {
        if (!text.trim() && !currentFile) return;
        if (status === 'chatting') setMessages(prev => [...prev, { role: 'user', text }]);

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
                setMessages(prev => [...prev, { role: 'assistant', text: '', status: 'Thinking...' }]);

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
            <header className={styles.header}>
                <div>
                    <h1>Shopping Advisor</h1>
                    <p>Get instant feedback on potential purchases.</p>
                </div>
                {user && (
                    <div className={styles.budgetBadge}>
                        {user.wallet_balance.toLocaleString()} {user.currency || 'TND'}
                    </div>
                )}
            </header>

            {status === 'idle' && !preview && (
                <div className={styles.dropzoneContainer}>
                    <label className={styles.dropzone}>
                        <input type="file" accept="image/*" onChange={handleFileChange} hidden />
                        <div className={styles.iconWrapper}>
                            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="17 8 12 3 7 8" /><line x1="12" y1="3" x2="12" y2="15" /></svg>
                        </div>
                        <h3>Upload Image</h3>
                        <p>Analyze clothing before you buy</p>
                    </label>
                </div>
            )}

            {preview && status === 'idle' && (
                <div className={styles.previewStep}>
                    <div className={styles.previewCard}>
                        <div className={styles.previewImageWrapper}>
                            <img src={preview} alt="item" />
                        </div>
                        <div className={styles.previewInfo}>
                            <h2>Analyze this?</h2>
                            <p>Glam will check versatility and your budget.</p>
                            <div className={styles.actionButtons}>
                                <button className={styles.primaryBtn} onClick={startAnalysis}>Start Analysis</button>
                                <button className={styles.ghostBtn} onClick={() => { setPreview(null); setFile(null); }}>Cancel</button>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {status === 'analyzing' && (
                <div className={styles.analyzingBox}>
                    <div className={styles.spinner} />
                    <p>Comparing with your wardrobe...</p>
                </div>
            )}

            {status === 'chatting' && (
                <div className={styles.chatContainer}>
                    <div className={styles.chatMain}>
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
                                <div>
                                    <small>Closet Matches</small>
                                    <div className={styles.matchMiniList}>
                                        {analysisData?.matches?.slice(0, 3).map((m: any, idx: number) => (
                                            <img key={idx} src={m.image_url} className={styles.matchMiniImg} />
                                        ))}
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div className={styles.chatMessages}>
                            {messages.map((msg, i) => (
                                <div key={i} className={`${styles.message} ${styles[msg.role]}`}>
                                    <div className={styles.bubble}>
                                        <div className={styles.textContent}>{renderMarkdown(msg.text)}</div>
                                        {msg.status && <div className={styles.streamingStatus}>{msg.status}</div>}
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

                        <div className={styles.chatInputArea}>
                            <div className={styles.inputWrapper}>
                                <input placeholder="Ask about this item..." value={input} onChange={(e) => setInput(e.target.value)} onKeyPress={(e) => e.key === 'Enter' && (setInput(''), sendToAI(input))} />
                            </div>
                            <button onClick={() => (setInput(''), sendToAI(input))} className={styles.sendBtn}>Send</button>
                        </div>
                    </div>
                </div>
            )}

            {tryOnData && userPhoto && <TryOnVisualizer bodyImage={userPhoto} items={tryOnData.items} tryonImageUrl={tryOnData.tryonImageUrl} onClose={() => setTryOnData(null)} />}
            <WalletConfirmationModal {...walletModalData} onClose={() => setWalletModalData(prev => ({ ...prev, isOpen: false }))} onSuccess={handlePurchaseSuccess} />
        </div>
    );
}
