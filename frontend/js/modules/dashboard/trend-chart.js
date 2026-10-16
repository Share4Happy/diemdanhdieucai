/**
 * ===================================================================
 * TREND CHART MODULE - THPT ĐIỀU CẢI DASHBOARD
 * Biểu Đồ Xu Hướng Sĩ Số Vắng 7 Ngày (Chart.js 4.4 Dual-Axis)
 * ===================================================================
 */

import { AttendanceAPI } from '../../api.js';

let trendChartInstance = null;

export function getTrendChartInstance() {
    return trendChartInstance;
}

export function resizeTrendChart() {
    if (trendChartInstance) {
        trendChartInstance.resize();
    }
}

export function generateFallbackTrendData(currentSession = null) {
    const days = ['16/09 (T4)', '17/09 (T5)', '18/09 (T6)', '19/09 (T7)', '20/09 (CN)', '21/09 (T2)', '22/09 (Hôm nay)'];
    const std = 1350;
    const curAbsent = currentSession ? currentSession.total_absent : 65;
    const pastAbsents = [45, 48, 52, 43, 39, 50, curAbsent];
    const avg = Math.round(pastAbsents.reduce((a, b) => a + b, 0) / pastAbsents.length);
    const diff = curAbsent - avg;

    return {
        days: days.map((lbl, idx) => ({
            label: lbl,
            absent: pastAbsents[idx],
            rate: Math.round((std - pastAbsents[idx]) / std * 1000) / 10,
            is_today: idx === days.length - 1
        })),
        avg_absent: avg,
        today_absent: curAbsent,
        assessment: {
            status: diff >= 15 ? 'danger' : (diff >= 5 ? 'warning' : 'normal'),
            text: diff > 0 ? `Tăng ${Math.abs(diff)} em so với mức TB` : `Ổn định quanh mức TB (${diff} em)`,
            diff: diff
        }
    };
}

export async function loadWeeklyTrendChart(opts = {}, currentSession = null) {
    const canvas = document.getElementById('trendWeeklyCanvas');
    if (!canvas) return;

    try {
        let trendData = null;
        try {
            trendData = await AttendanceAPI.get7DaysTrend(opts);
        } catch (e) {
            console.warn('Lỗi kết nối /trend-7days, tự động dùng dữ liệu dự phòng:', e);
        }

        if (!trendData || !trendData.days || trendData.days.length === 0) {
            trendData = generateFallbackTrendData(currentSession);
        }

        // Đồng bộ dữ liệu ngày hôm nay với ca quét hiện tại
        if (currentSession && trendData.days && trendData.days.length > 0) {
            const lastIdx = trendData.days.length - 1;
            if (currentSession.total_absent !== undefined && currentSession.total_absent !== null) {
                trendData.days[lastIdx].absent = currentSession.total_absent;
                const std = currentSession.total_standard || 1350;
                const prs = currentSession.total_present || (std - currentSession.total_absent);
                trendData.days[lastIdx].rate = Math.round((prs / std) * 1000) / 10;
                trendData.today_absent = currentSession.total_absent;

                const diff = trendData.today_absent - trendData.avg_absent;
                if (diff >= 15) {
                    trendData.assessment = {
                        status: 'danger',
                        text: `Cao hơn trung bình tuần (+${Math.round(diff)} em) • Bất thường cần kiểm tra`,
                        diff: diff
                    };
                } else if (diff >= 5) {
                    trendData.assessment = {
                        status: 'warning',
                        text: `Tăng nhẹ so với trung bình (+${Math.round(diff)} em) • Cần theo dõi`,
                        diff: diff
                    };
                } else if (diff <= -8) {
                    trendData.assessment = {
                        status: 'success',
                        text: `Thấp hơn mức trung bình (${Math.round(diff)} em) • Rất tốt`,
                        diff: diff
                    };
                } else {
                    const diffStr = diff >= 0 ? `+${Math.round(diff)}` : `${Math.round(diff)}`;
                    trendData.assessment = {
                        status: 'normal',
                        text: `Ổn định quanh mức trung bình (${diffStr} em)`,
                        diff: diff
                    };
                }
            }
        }

        const todayAbsentEl = document.getElementById('trendChipTodayAbsent');
        const avgAbsentEl = document.getElementById('trendChipAvgAbsent');
        const assessBadge = document.getElementById('trendAssessmentBadge');

        const todayObj = trendData.days[trendData.days.length - 1];
        const todayAbsent = todayObj ? todayObj.absent : (currentSession?.total_absent || 0);
        const todayRate = todayObj ? todayObj.rate : 95.2;

        if (todayAbsentEl) {
            todayAbsentEl.textContent = `${todayAbsent} em (${todayRate}%)`;
        }

        if (avgAbsentEl) {
            avgAbsentEl.textContent = `~${trendData.avg_absent} em/ngày`;
        }

        if (assessBadge && trendData.assessment) {
            const status = trendData.assessment.status || 'normal';
            assessBadge.className = `assessment-status-badge status-${status}`;
            let iconHtml = '<i class="fa-solid fa-circle-info"></i>';
            if (status === 'danger') iconHtml = '<i class="fa-solid fa-triangle-exclamation"></i>';
            else if (status === 'warning') iconHtml = '<i class="fa-solid fa-arrow-trend-up"></i>';
            else if (status === 'success') iconHtml = '<i class="fa-solid fa-circle-check"></i>';

            assessBadge.innerHTML = `${iconHtml} ${trendData.assessment.text}`;
        }

        if (typeof Chart === 'undefined') {
            console.warn('Thư viện Chart.js chưa tải xong, sẽ thử lại sau 300ms.');
            setTimeout(() => loadWeeklyTrendChart(opts, currentSession), 300);
            return;
        }

        renderTrendLineChart(canvas, trendData);

    } catch (err) {
        console.error('Lỗi khi dựng biểu đồ xu hướng 7 ngày:', err);
    }
}

export function renderTrendLineChart(canvas, trendData) {
    const ctx = canvas.getContext('2d');

    if (trendChartInstance) {
        trendChartInstance.destroy();
        trendChartInstance = null;
    }

    const labels = trendData.days.map(d => d.label);
    const absentValues = trendData.days.map(d => d.absent);
    const rateValues = trendData.days.map(d => d.rate);
    const avgAbsent = trendData.avg_absent || 48;

    const maxAbsent = Math.max(...absentValues, 0);
    let yMax = 1600;
    let yStep = 400;

    if (maxAbsent > 800) {
        yMax = 1600;
        yStep = 400;
    } else if (maxAbsent > 400) {
        yMax = 1200;
        yStep = 400;
    } else if (maxAbsent > 150) {
        yMax = 800;
        yStep = 200;
    } else {
        yMax = Math.max(120, Math.ceil((maxAbsent * 1.55) / 20) * 20);
        yStep = yMax / 4;
    }

    const minRate = Math.min(...rateValues);
    let y1Min = 80;
    let y1Max = 110;
    let y1Step = 5;
    if (minRate < 80) {
        y1Min = 0;
        y1Max = 110;
        y1Step = 25;
    } else if (minRate < 90) {
        y1Min = Math.max(0, Math.floor(minRate / 5) * 5 - 5);
        y1Max = 105;
        y1Step = 5;
    } else {
        y1Min = 85;
        y1Max = 105;
        y1Step = 5;
    }

    const gradient = ctx.createLinearGradient(0, 0, 0, 260);
    gradient.addColorStop(0, 'rgba(239, 68, 68, 0.20)');
    gradient.addColorStop(0.7, 'rgba(239, 68, 68, 0.03)');
    gradient.addColorStop(1, 'rgba(239, 68, 68, 0.0)');

    const valueBadgesPlugin = {
        id: 'valueBadgesPlugin',
        afterDatasetsDraw(chart) {
            const chartCtx = chart.ctx;
            const metaAbsent = chart.getDatasetMeta(0);
            if (!metaAbsent || !metaAbsent.data || metaAbsent.hidden) return;

            chartCtx.save();
            chartCtx.font = 'bold 11px Inter, system-ui, -apple-system, sans-serif';
            chartCtx.textAlign = 'center';
            chartCtx.textBaseline = 'middle';

            metaAbsent.data.forEach((point, index) => {
                const val = absentValues[index];
                if (val === undefined || val === null) return;
                const isToday = trendData.days[index]?.is_today;

                if (isToday) {
                    const text = `${val} em`;
                    const textWidth = chartCtx.measureText(text).width;
                    const padX = 8;
                    const rectW = textWidth + padX * 2;
                    const rectH = 22;

                    const drawBelow = point.y < 42;
                    const rectX = point.x - rectW / 2;
                    const rectY = drawBelow ? point.y + 10 : point.y - rectH - 8;

                    chartCtx.fillStyle = '#dc2626';
                    if (typeof chartCtx.roundRect === 'function') {
                        chartCtx.beginPath();
                        chartCtx.roundRect(rectX, rectY, rectW, rectH, 5);
                        chartCtx.fill();
                    } else {
                        chartCtx.fillRect(rectX, rectY, rectW, rectH);
                    }

                    chartCtx.beginPath();
                    if (drawBelow) {
                        chartCtx.moveTo(point.x - 4, rectY);
                        chartCtx.lineTo(point.x + 4, rectY);
                        chartCtx.lineTo(point.x, rectY - 5);
                    } else {
                        chartCtx.moveTo(point.x - 4, rectY + rectH);
                        chartCtx.lineTo(point.x + 4, rectY + rectH);
                        chartCtx.lineTo(point.x, rectY + rectH + 5);
                    }
                    chartCtx.closePath();
                    chartCtx.fill();

                    chartCtx.fillStyle = '#ffffff';
                    chartCtx.fillText(text, point.x, rectY + rectH / 2);
                } else {
                    const text = `${val}`;
                    const textWidth = chartCtx.measureText(text).width;
                    const padX = 6;
                    const rectW = Math.max(22, textWidth + padX * 2);
                    const rectH = 17;

                    const drawBelow = point.y < 35;
                    const rectX = point.x - rectW / 2;
                    const rectY = drawBelow ? point.y + 8 : point.y - rectH - 6;

                    chartCtx.fillStyle = 'rgba(255, 255, 255, 0.94)';
                    chartCtx.beginPath();
                    if (typeof chartCtx.roundRect === 'function') {
                        chartCtx.roundRect(rectX, rectY, rectW, rectH, 4);
                    } else {
                        chartCtx.fillRect(rectX, rectY, rectW, rectH);
                    }
                    chartCtx.fill();
                    chartCtx.strokeStyle = 'rgba(203, 213, 225, 0.9)';
                    chartCtx.lineWidth = 1;
                    chartCtx.stroke();

                    chartCtx.fillStyle = '#1e293b';
                    chartCtx.fillText(text, point.x, rectY + rectH / 2);
                }
            });

            const metaAvg = chart.getDatasetMeta(1);
            if (metaAvg && metaAvg.data && metaAvg.data.length > 0 && !metaAvg.hidden) {
                const lastPt = metaAvg.data[metaAvg.data.length - 1];
                const text = `TB: ${Math.round(avgAbsent)} em`;
                const textW = chartCtx.measureText(text).width;
                const badgeW = textW + 14;
                const badgeH = 18;
                const badgeX = lastPt.x - badgeW - 8;
                const badgeY = lastPt.y - badgeH / 2;

                chartCtx.fillStyle = 'rgba(248, 250, 252, 0.95)';
                chartCtx.beginPath();
                if (typeof chartCtx.roundRect === 'function') {
                    chartCtx.roundRect(badgeX, badgeY, badgeW, badgeH, 4);
                } else {
                    chartCtx.fillRect(badgeX, badgeY, badgeW, badgeH);
                }
                chartCtx.fill();
                chartCtx.strokeStyle = '#cbd5e1';
                chartCtx.lineWidth = 1;
                chartCtx.stroke();

                chartCtx.font = '600 10.5px Inter, system-ui, sans-serif';
                chartCtx.fillStyle = '#475569';
                chartCtx.fillText(text, badgeX + badgeW / 2, badgeY + badgeH / 2);
            }

            chartCtx.restore();
        }
    };

    trendChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Số học sinh vắng (em)',
                    data: absentValues,
                    borderColor: '#ef4444',
                    backgroundColor: gradient,
                    borderWidth: 3.2,
                    tension: 0.32,
                    fill: true,
                    pointRadius: trendData.days.map(d => d.is_today ? 7 : 5),
                    pointBackgroundColor: trendData.days.map(d => d.is_today ? '#dc2626' : '#ffffff'),
                    pointBorderColor: '#dc2626',
                    pointBorderWidth: 2.5,
                    pointHoverRadius: trendData.days.map(d => d.is_today ? 9 : 7.5),
                    pointHoverBackgroundColor: '#dc2626',
                    pointHoverBorderColor: '#ffffff',
                    pointHoverBorderWidth: 2.5,
                    yAxisID: 'y'
                },
                {
                    label: `Trung bình tuần (~${Math.round(avgAbsent)} em)`,
                    data: trendData.days.map(() => avgAbsent),
                    borderColor: '#94a3b8',
                    borderDash: [6, 6],
                    borderWidth: 1.8,
                    pointRadius: 0,
                    fill: false,
                    yAxisID: 'y'
                },
                {
                    label: 'Tỷ lệ chuyên cần (%)',
                    data: rateValues,
                    borderColor: '#059669',
                    borderDash: [3, 3],
                    borderWidth: 2.2,
                    pointRadius: 4,
                    pointBackgroundColor: '#ffffff',
                    pointBorderColor: '#059669',
                    pointBorderWidth: 2,
                    pointHoverRadius: 6,
                    tension: 0.32,
                    fill: false,
                    yAxisID: 'y1'
                }
            ]
        },
        plugins: [valueBadgesPlugin],
        options: {
            responsive: true,
            maintainAspectRatio: false,
            layout: {
                padding: {
                    top: 25,
                    right: 15,
                    bottom: 6,
                    left: 8
                }
            },
            interaction: {
                mode: 'index',
                intersect: false
            },
            plugins: {
                legend: {
                    display: true,
                    position: 'bottom',
                    align: 'center',
                    labels: {
                        boxWidth: 12,
                        boxHeight: 12,
                        usePointStyle: true,
                        pointStyle: 'circle',
                        font: {
                            family: 'Inter, system-ui, -apple-system, sans-serif',
                            size: 12,
                            weight: '600'
                        },
                        padding: 18
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(15, 23, 42, 0.95)',
                    titleFont: {
                        family: 'Inter, system-ui, sans-serif',
                        size: 12.5,
                        weight: '700'
                    },
                    bodyFont: {
                        family: 'Inter, system-ui, sans-serif',
                        size: 11.5,
                        weight: '500'
                    },
                    padding: 12,
                    cornerRadius: 8,
                    boxPadding: 5,
                    callbacks: {
                        label: function (context) {
                            const dsLabel = context.dataset.label || '';
                            const val = context.parsed.y;
                            if (context.dataset.yAxisID === 'y1') {
                                return ` ${dsLabel}: ${val}%`;
                            }
                            if (context.datasetIndex === 0) {
                                const diff = Math.round(val - avgAbsent);
                                const diffStr = diff > 0 ? `(+${diff} so với TB)` : `(${diff} so với TB)`;
                                return ` ${dsLabel}: ${val} em ${diffStr}`;
                            }
                            return ` ${dsLabel}`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    min: 0,
                    max: yMax,
                    title: {
                        display: true,
                        text: 'Vắng (em)',
                        font: { family: 'Inter, sans-serif', size: 11, weight: '700' },
                        color: '#dc2626'
                    },
                    grid: {
                        color: '#f1f5f9',
                        borderDash: [4, 4]
                    },
                    ticks: {
                        stepSize: yStep,
                        font: { family: 'Inter, sans-serif', size: 11, weight: '600' },
                        color: '#64748b',
                        callback: v => v + ' em'
                    }
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    min: y1Min,
                    max: y1Max,
                    title: {
                        display: true,
                        text: 'Chuyên cần (%)',
                        font: { family: 'Inter, sans-serif', size: 11, weight: '700' },
                        color: '#059669'
                    },
                    grid: {
                        drawOnChartArea: false
                    },
                    ticks: {
                        stepSize: y1Step,
                        callback: v => {
                            if (v > 100) return '';
                            return v + '%';
                        },
                        font: { family: 'Inter, sans-serif', size: 11, weight: '600' },
                        color: '#059669'
                    }
                },
                x: {
                    grid: {
                        display: false
                    },
                    ticks: {
                        font: { family: 'Inter, sans-serif', size: 11.5, weight: '600' },
                        color: '#334155'
                    }
                }
            }
        }
    });
}
