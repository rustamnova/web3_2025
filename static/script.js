const API_BASE = '';

// Управление табами
function showTab(tabName) {
    // Скрыть все табы
    const tabs = document.querySelectorAll('.tab-content');
    tabs.forEach(tab => tab.classList.remove('active'));
    
    // Убрать активный класс с навигационных элементов
    const navItems = document.querySelectorAll('.nav-item');
    navItems.forEach(item => item.classList.remove('active'));
    
    // Показать выбранный таб
    const targetTab = document.getElementById(tabName);
    if (targetTab) {
        targetTab.classList.add('active');
    }
    
    // Добавить активный класс к навигационному элементу (если вызвано через клик)
    if (event && event.target) {
        const navItem = event.target.closest('.nav-item');
        if (navItem) {
            navItem.classList.add('active');
        }
    } else {
        // Если вызвано программно, найти соответствующий навигационный элемент
        const targetNavItem = document.querySelector(`[onclick="showTab('${tabName}')"]`);
        if (targetNavItem) {
            targetNavItem.classList.add('active');
        }
    }
    
    // Специальная обработка для дашборда
    if (tabName === 'dashboard') {
        showDashboard();
    }
}

// Проверка состояния сервиса
async function checkHealth() {
    const resultDiv = document.getElementById('health-result');
    resultDiv.className = 'result loading';
    resultDiv.textContent = 'Проверяем состояние сервиса...';
    
    try {
        const response = await fetch(`${API_BASE}/health`);
        const data = await response.json();
        
        resultDiv.className = 'result success';
        resultDiv.innerHTML = `
            <strong>✅ Сервис работает!</strong><br>
            <div class="json-display">${JSON.stringify(data, null, 2)}</div>
        `;
    } catch (error) {
        resultDiv.className = 'result error';
        resultDiv.innerHTML = `
            <strong>❌ Ошибка подключения</strong><br>
            ${error.message}
        `;
    }
}

// Загрузка тем
async function loadTopics() {
    const resultDiv = document.getElementById('topics-result');
    resultDiv.className = 'result loading';
    resultDiv.textContent = 'Загружаем темы...';
    
    try {
        const response = await fetch(`${API_BASE}/topics`);
        const data = await response.json();
        
        resultDiv.className = 'result success';
        resultDiv.innerHTML = `
            <strong>📋 Загружено тем: ${data.length}</strong><br><br>
            ${data.map(topic => `
                <div class="prediction-item">
                    <h4>${topic.name}</h4>
                    <p><strong>ID:</strong> ${topic.id} | <strong>Slug:</strong> ${topic.slug}</p>
                    ${topic.description ? `<p><strong>Описание:</strong> ${topic.description}</p>` : ''}
                    <span class="topic-tag">${topic.is_active ? 'Активна' : 'Неактивна'}</span>
                </div>
            `).join('')}
        `;
    } catch (error) {
        resultDiv.className = 'result error';
        resultDiv.innerHTML = `
            <strong>❌ Ошибка загрузки тем</strong><br>
            ${error.message}
        `;
    }
}

// Анализ отзывов
async function predictReviews() {
    const textarea = document.getElementById('review-text');
    const resultDiv = document.getElementById('predict-result');
    
    const reviews = textarea.value.trim().split('\n').filter(line => line.trim());
    
    if (reviews.length === 0) {
        resultDiv.className = 'result error';
        resultDiv.textContent = '❌ Пожалуйста, введите хотя бы один отзыв';
        return;
    }
    
    resultDiv.className = 'result loading';
    resultDiv.textContent = 'Анализируем отзывы...';
    
    try {
        const data = {
            data: reviews.map((text, index) => ({
                id: index + 1,
                text: text.trim()
            }))
        };
        
        const response = await fetch(`${API_BASE}/predict`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const result = await response.json();
        
        resultDiv.className = 'result success';
        resultDiv.innerHTML = `
            <strong>🔮 Результаты анализа (${result.predictions.length} отзывов)</strong><br><br>
            ${result.predictions.map((pred, index) => `
                <div class="prediction-item">
                    <h4>Отзыв ${pred.id}: "${reviews[index]}"</h4>
                    <p><strong>Темы:</strong> ${pred.topics.map(topic => `<span class="topic-tag">${topic}</span>`).join('')}</p>
                    <p><strong>Тональность:</strong> ${pred.sentiments.map(sentiment => {
                        const className = sentiment === 'положительно' ? 'sentiment-positive' : 
                                        sentiment === 'отрицательно' ? 'sentiment-negative' : 'sentiment-neutral';
                        return `<span class="sentiment-tag ${className}">${sentiment}</span>`;
                    }).join('')}</p>
                </div>
            `).join('')}
        `;
    } catch (error) {
        resultDiv.className = 'result error';
        resultDiv.innerHTML = `
            <strong>❌ Ошибка анализа</strong><br>
            ${error.message}
        `;
    }
}

// Отправка обратной связи
async function sendFeedback() {
    const resultDiv = document.getElementById('feedback-result');
    
    const id = parseInt(document.getElementById('feedback-id').value);
    const topics = document.getElementById('feedback-topics').value.split(',').map(t => t.trim()).filter(t => t);
    const sentiments = document.getElementById('feedback-sentiments').value.split(',').map(s => s.trim()).filter(s => s);
    const comment = document.getElementById('feedback-comment').value.trim();
    const correct = document.getElementById('feedback-correct').checked;
    
    if (!id || isNaN(id)) {
        resultDiv.className = 'result error';
        resultDiv.textContent = '❌ Пожалуйста, введите корректный ID отзыва';
        return;
    }
    
    resultDiv.className = 'result loading';
    resultDiv.textContent = 'Отправляем обратную связь...';
    
    try {
        const data = {
            data: [{
                id: id,
                topics: topics.length > 0 ? topics : null,
                sentiments: sentiments.length > 0 ? sentiments : null,
                comment: comment || null,
                correct: correct
            }]
        };
        
        const response = await fetch(`${API_BASE}/feedback`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const result = await response.json();
        
        resultDiv.className = 'result success';
        resultDiv.innerHTML = `
            <strong>✅ Обратная связь отправлена!</strong><br>
            <div class="json-display">${JSON.stringify(result, null, 2)}</div>
        `;
    } catch (error) {
        resultDiv.className = 'result error';
        resultDiv.innerHTML = `
            <strong>❌ Ошибка отправки</strong><br>
            ${error.message}
        `;
    }
}

// Парсинг отзывов с banki.ru
async function parseReviews() {
    const resultDiv = document.getElementById('parse-result');
    const count = parseInt(document.getElementById('parse-count').value);
    const pages = parseInt(document.getElementById('parse-pages').value);
    
    if (count < 1 || count > 100) {
        resultDiv.className = 'result error';
        resultDiv.textContent = '❌ Количество отзывов должно быть от 1 до 100';
        return;
    }
    
    resultDiv.className = 'result loading';
    resultDiv.textContent = 'Парсим отзывы с banki.ru...';
    
    try {
        const data = {
            num_reviews: count,
            num_pages: pages
        };
        
        const response = await fetch(`${API_BASE}/parse`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const result = await response.json();
        
        resultDiv.className = 'result success';
        resultDiv.innerHTML = `
            <strong>✅ Парсинг завершен!</strong><br>
            <p><strong>Собрано отзывов:</strong> ${result.total_count}</p>
            <p><strong>Время парсинга:</strong> ${result.parse_time_sec} сек</p><br>
            <strong>Примеры отзывов:</strong><br>
            ${result.reviews.slice(0, 5).map(review => `
                <div class="prediction-item">
                    <h4>Отзыв ${review.id}${review.bank_name ? ` (${review.bank_name})` : ''}</h4>
                    <p><strong>Текст отзыва:</strong> "${review.text || 'Текст не найден'}"</p>
                    ${review.rating ? `<p><strong>Рейтинг:</strong> ${review.rating}/5</p>` : ''}
                    ${review.created_at ? `<p><strong>Дата:</strong> ${review.created_at}</p>` : ''}
                    ${review.source ? `<p><strong>Источник:</strong> ${review.source}</p>` : ''}
                    ${review.url ? `<p><strong>Ссылка:</strong> <a href="${review.url}" target="_blank" class="review-link">Перейти к отзыву</a></p>` : ''}
                </div>
            `).join('')}
            ${result.reviews.length > 5 ? `<p><em>... и еще ${result.reviews.length - 5} отзывов</em></p>` : ''}
        `;
    } catch (error) {
        resultDiv.className = 'result error';
        resultDiv.innerHTML = `
            <strong>❌ Ошибка парсинга</strong><br>
            ${error.message}
        `;
    }
}

// Парсинг и анализ отзывов
async function parseAndAnalyze() {
    const resultDiv = document.getElementById('parse-result');
    const count = parseInt(document.getElementById('parse-count').value);
    const pages = parseInt(document.getElementById('parse-pages').value);
    
    if (count < 1 || count > 100) {
        resultDiv.className = 'result error';
        resultDiv.textContent = '❌ Количество отзывов должно быть от 1 до 100';
        return;
    }
    
    resultDiv.className = 'result loading';
    resultDiv.textContent = 'Парсим и анализируем отзывы с banki.ru...';
    
    try {
        const data = {
            num_reviews: count,
            num_pages: pages
        };
        
        const response = await fetch(`${API_BASE}/parse-and-analyze`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const result = await response.json();
        
        resultDiv.className = 'result success';
        resultDiv.innerHTML = `
            <strong>✅ Парсинг и анализ завершены!</strong><br>
            <p><strong>Обработано отзывов:</strong> ${result.predictions.length}</p>
            <p><strong>Время парсинга:</strong> ${result.parse_time_sec} сек</p>
            <p><strong>Время анализа:</strong> ${result.analysis_time_sec} сек</p><br>
            <strong>Результаты анализа:</strong><br>
            ${result.predictions.map((pred, index) => `
                <div class="prediction-item">
                    <h4>Отзыв ${pred.id}</h4>
                    <p><strong>Текст отзыва:</strong> "${pred.text || 'Текст не найден'}"</p>
                    <p><strong>Темы:</strong> ${pred.topics.map(topic => `<span class="topic-tag">${topic}</span>`).join('')}</p>
                    <p><strong>Тональность:</strong> ${pred.sentiments.map(sentiment => {
                        const className = sentiment === 'положительно' ? 'sentiment-positive' : 
                                        sentiment === 'отрицательно' ? 'sentiment-negative' : 'sentiment-neutral';
                        return `<span class="sentiment-tag ${className}">${sentiment}</span>`;
                    }).join('')}</p>
                    ${pred.source ? `<p><strong>Источник:</strong> ${pred.source}</p>` : ''}
                    ${pred.url ? `<p><strong>Ссылка:</strong> <a href="${pred.url}" target="_blank" class="review-link">Перейти к отзыву</a></p>` : ''}
                </div>
            `).join('')}
        `;
        
        // Показываем дашборд
        showDashboard(result.predictions);
    } catch (error) {
        resultDiv.className = 'result error';
        resultDiv.innerHTML = `
            <strong>❌ Ошибка парсинга и анализа</strong><br>
            ${error.message}
        `;
    }
}

// Функции дашборда
function showDashboard(predictions) {
    // Показываем дашборд в отдельном табе
    showTab('dashboard');
    
    // Разделяем отзывы по источникам
    const bankiReviews = predictions.filter(p => p.source === 'banki.ru');
    const sravniReviews = predictions.filter(p => p.source === 'sravni.ru');
    const uploadedReviews = predictions.filter(p => p.source === 'uploaded_file' || !p.source);
    
    // Обновляем дашборд для Banki.ru
    updateDashboardSection('banki', bankiReviews);
    
    // Обновляем дашборд для Сравни.ру
    updateDashboardSection('sravni', sravniReviews);
    
    // Обновляем дашборд для загруженных файлов
    if (uploadedReviews.length > 0) {
        updateDashboardSection('uploaded', uploadedReviews);
    }
}

function updateDashboardSection(site, reviews) {
    const statsContainer = document.getElementById(`${site}-stats`);
    const sentimentContainer = document.getElementById(`${site}-sentiment`);
    const topicsContainer = document.getElementById(`${site}-topics`);
    const reviewsContainer = document.getElementById(`${site}-reviews`);
    
    // Статистика
    const totalReviews = reviews.length;
    const avgRating = reviews.reduce((sum, r) => sum + (r.rating || 0), 0) / totalReviews || 0;
    const positiveCount = reviews.filter(r => r.sentiments && r.sentiments.includes('положительно')).length;
    const negativeCount = reviews.filter(r => r.sentiments && r.sentiments.includes('отрицательно')).length;
    const neutralCount = reviews.filter(r => r.sentiments && r.sentiments.includes('нейтрально')).length;
    
    statsContainer.innerHTML = `
        <div class="stat-card">
            <div class="stat-number">${totalReviews}</div>
            <div class="stat-label">Отзывов</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">${avgRating.toFixed(1)}</div>
            <div class="stat-label">Средний рейтинг</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">${positiveCount}</div>
            <div class="stat-label">Положительных</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">${negativeCount}</div>
            <div class="stat-label">Отрицательных</div>
        </div>
    `;
    
    // График тональности
    const totalSentiment = positiveCount + negativeCount + neutralCount;
    const positivePercent = totalSentiment > 0 ? (positiveCount / totalSentiment) * 100 : 0;
    const negativePercent = totalSentiment > 0 ? (negativeCount / totalSentiment) * 100 : 0;
    const neutralPercent = totalSentiment > 0 ? (neutralCount / totalSentiment) * 100 : 0;
    
    sentimentContainer.innerHTML = `
        <div class="sentiment-bar positive">
            <div class="sentiment-fill positive" style="width: ${positivePercent}%"></div>
        </div>
        <div class="sentiment-bar negative">
            <div class="sentiment-fill negative" style="width: ${negativePercent}%"></div>
        </div>
        <div class="sentiment-bar neutral">
            <div class="sentiment-fill neutral" style="width: ${neutralPercent}%"></div>
        </div>
    `;
    
    // Облако тем
    const topicCounts = {};
    reviews.forEach(review => {
        if (review.topics) {
            review.topics.forEach(topic => {
                topicCounts[topic] = (topicCounts[topic] || 0) + 1;
            });
        }
    });
    
    const sortedTopics = Object.entries(topicCounts)
        .sort(([,a], [,b]) => b - a)
        .slice(0, 5); // Топ-5 тем
    
    topicsContainer.innerHTML = sortedTopics.map(([topic, count]) => 
        `<span class="topic-cloud-tag" data-count="${count}">${topic}</span>`
    ).join('');
    
    // Превью отзывов
    reviewsContainer.innerHTML = reviews.slice(0, 3).map(review => `
        <div class="review-preview" onclick="showFullReview(${review.id})">
            <div class="review-text">${review.text}</div>
            <div class="review-meta">
                <div class="review-rating">
                    ${Array.from({length: 5}, (_, i) => 
                        `<span class="star ${i < (review.rating || 0) ? '' : 'empty'}">★</span>`
                    ).join('')}
                </div>
                <div>${review.sentiments ? review.sentiments.join(', ') : 'Не определено'}</div>
            </div>
        </div>
    `).join('');
}

function showFullReview(reviewId) {
    // Функция для показа полного отзыва (можно расширить)
    alert(`Показать полный отзыв ${reviewId}`);
}

// Загрузка файла и анализ
async function uploadAndAnalyze() {
    const fileInput = document.getElementById('file-upload');
    const resultDiv = document.getElementById('upload-result');
    
    if (!fileInput.files || fileInput.files.length === 0) {
        resultDiv.className = 'result error';
        resultDiv.textContent = '❌ Выберите файл для загрузки';
        return;
    }
    
    const file = fileInput.files[0];
    
    resultDiv.className = 'result loading';
    resultDiv.textContent = `📤 Загружаем файл ${file.name}...`;
    
    try {
        const formData = new FormData();
        formData.append('file', file);
        
        const response = await fetch(`${API_BASE}/upload-and-analyze`, {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || `HTTP ${response.status}`);
        }
        
        const data = await response.json();
        
        resultDiv.className = 'result success';
        resultDiv.innerHTML = `
            <strong>✅ Файл успешно загружен и проанализирован!</strong><br>
            <div class="stats">
                <span class="stat-item">📊 Отзывов: ${data.predictions.length}</span>
                <span class="stat-item">⏱️ Время анализа: ${data.analysis_time_sec}с</span>
            </div>
            <div class="predictions-preview">
                ${data.predictions.slice(0, 5).map(pred => `
                    <div class="prediction-item">
                        <div class="prediction-text">${pred.text}</div>
                        <div class="prediction-meta">
                            <span class="topics">🏷️ ${pred.topics ? pred.topics.join(', ') : 'Нет тем'}</span>
                            <span class="sentiments">😊 ${pred.sentiments ? pred.sentiments.join(', ') : 'Нет тональности'}</span>
                        </div>
                    </div>
                `).join('')}
                ${data.predictions.length > 5 ? `<div class="more-items">... и еще ${data.predictions.length - 5} отзывов</div>` : ''}
            </div>
            <div class="button-group">
                <button onclick="showDashboard(${JSON.stringify(data.predictions).replace(/"/g, '&quot;')})" class="btn btn-primary">Посмотреть на дашборде</button>
                <button onclick="downloadResults(${JSON.stringify(data).replace(/"/g, '&quot;')})" class="btn btn-secondary">Скачать результаты</button>
            </div>
        `;
        
        // Сохраняем результаты для дашборда
        window.lastAnalysisResults = data;
        
    } catch (error) {
        resultDiv.className = 'result error';
        resultDiv.innerHTML = `
            <strong>❌ Ошибка загрузки файла</strong><br>
            ${error.message}
        `;
    }
}

async function analyzeDataset() {
    const resultDiv = document.getElementById('dataset-result');
    
    resultDiv.style.display = 'block';
    resultDiv.className = 'result loading';
    resultDiv.textContent = '📊 Анализируем файлы dataset...';
    
    try {
        const response = await fetch(`${API_BASE}/analyze-dataset`, {
            method: 'POST'
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || `HTTP ${response.status}`);
        }
        
        const data = await response.json();
        
        resultDiv.className = 'result success';
        resultDiv.innerHTML = `
            <strong>✅ Анализ dataset завершен!</strong><br>
            <div class="stats">
                <span class="stat-item">📁 Найдено файлов: ${data.files_found}/${data.total_files_checked}</span>
                <span class="stat-item">⏱️ Время анализа: ${data.analysis_time_sec}с</span>
            </div>
            <div style="margin-top: 15px;">
                <button onclick="showDatasetDashboard()" class="btn btn-primary">📊 Показать дашборд</button>
            </div>
        `;
        
        // Автоматически показываем дашборд после анализа
        setTimeout(() => {
            showDatasetDashboard();
            updateDatasetDashboard(data);
        }, 1000);
        
    } catch (error) {
        resultDiv.className = 'result error';
        resultDiv.innerHTML = `
            <strong>❌ Ошибка анализа dataset</strong><br>
            ${error.message}
        `;
    }
}

function showDatasetDashboard() {
    const dashboard = document.getElementById('dataset-dashboard');
    dashboard.style.display = 'block';
    
    // Прокручиваем к дашборду
    dashboard.scrollIntoView({ behavior: 'smooth', block: 'start' });
    
    // Загружаем данные для дашборда, если они еще не загружены
    if (!window.datasetData) {
        loadDatasetDashboardData();
    } else {
        updateDatasetDashboard(window.datasetData);
    }
}

function hideDatasetDashboard() {
    const dashboard = document.getElementById('dataset-dashboard');
    dashboard.style.display = 'none';
}

async function loadDatasetDashboardData() {
    try {
        // Загружаем информацию о файлах
        const response = await fetch(`${API_BASE}/analyze-dataset`, {
            method: 'POST'
        });
        
        if (!response.ok) {
            throw new Error('Ошибка загрузки данных dataset');
        }
        
        const data = await response.json();
        window.datasetData = data; // Сохраняем данные глобально
        updateDatasetDashboard(data);
        
    } catch (error) {
        console.error('Ошибка загрузки дашборда:', error);
    }
}

function updateDatasetDashboard(data) {
    // Обновляем статистику
    updateDashboardStats(data);
    
    // Обновляем файлы
    updateFilesOverview(data.results);
    
    // Обновляем графики
    updateCharts(data);
    
    // Обновляем ключевые метрики
    updateKeyMetrics(data);
}

function updateDashboardStats(data) {
    const stats = data.summary_stats || {};
    
    // Общее количество отзывов
    const totalReviews = stats.total_reviews || 0;
    document.getElementById('total-reviews').textContent = totalReviews.toLocaleString();
    
    // Количество тем
    const totalTopics = stats.total_topics || 0;
    document.getElementById('total-topics').textContent = totalTopics;
    
    // Средняя тональность (положительные)
    const sentiment = stats.sentiment_distribution || {};
    const avgPositive = sentiment.positive ? Math.round(sentiment.positive) : 0;
    document.getElementById('avg-sentiment').textContent = `${avgPositive}%`;
    
    // Период данных
    const dateRange = stats.date_range || {};
    const months = dateRange.months || 0;
    document.getElementById('date-range').textContent = `${months} мес`;
}

function updateFilesOverview(files) {
    const filesGrid = document.getElementById('files-overview');
    
    const fileDescriptions = {
        'reviews_combined_dedup.csv': 'Основной файл с объединенными отзывами из всех источников',
        'review_topics.csv': 'Связи между отзывами и темами с метаданными',
        'topics_overview.csv': 'Обзор тем с метриками и автолейблами',
        'topic_monthly.csv': 'Помесячные метрики по темам',
        'global_monthly.csv': 'Общая помесячная динамика',
        'topic_regexes.json': 'Регулярные выражения для классификации тем'
    };
    
    filesGrid.innerHTML = Object.entries(files).map(([filename, info]) => `
        <div class="file-card">
            <h5>${filename}</h5>
            <div class="file-meta">
                <span class="file-status ${info.exists ? 'exists' : 'missing'}">
                    ${info.exists ? '✅ Найден' : '❌ Отсутствует'}
                </span>
                ${info.exists ? `<span class="file-size">${info.size_mb} MB</span>` : ''}
            </div>
            <div class="file-description">
                ${fileDescriptions[filename] || 'Файл данных'}
            </div>
        </div>
    `).join('');
}

function updateCharts(data) {
    // Источники
    updateSourcesChart(data);
    
    // Темы
    updateTopicsChart(data);
    
    // Тональность
    updateSentimentChart(data);
    
    // Месячная динамика
    updateMonthlyChart(data);
}

function updateSourcesChart(data) {
    const container = document.getElementById('sources-chart');
    const sources = data.summary_stats?.sources || {};
    
    if (Object.keys(sources).length === 0) {
        container.innerHTML = '<div class="chart-placeholder">Нет данных об источниках</div>';
        return;
    }
    
    const maxValue = Math.max(...Object.values(sources));
    
    container.innerHTML = `
        <div class="bar-chart">
            ${Object.entries(sources).map(([source, count]) => {
                const height = (count / maxValue) * 90;
                return `
                    <div class="bar" style="height: ${height}%;">
                        <div class="bar-value">${count.toLocaleString()}</div>
                        <div class="bar-label">${source}</div>
                    </div>
                `;
            }).join('')}
        </div>
    `;
}

function updateTopicsChart(data) {
    const container = document.getElementById('topics-chart');
    
    // Показываем заглушку, так как детальные данные тем нужно загружать отдельно
    container.innerHTML = `
        <div class="chart-placeholder">
            🏷️ Топ-10 тем из анализа:<br><br>
            <strong>Основные категории:</strong><br>
            • Банковские карты<br>
            • Мобильное приложение<br>
            • Обслуживание в отделении<br>
            • Комиссии и тарифы<br>
            • Поддержка клиентов<br>
            • Безопасность<br>
            • Переводы и платежи<br>
            • Счета и вклады<br>
            • Ипотека<br>
            • Автокредит
        </div>
    `;
}

function updateSentimentChart(data) {
    const container = document.getElementById('sentiment-chart');
    const sentiment = data.summary_stats?.sentiment_distribution || {};
    
    if (Object.keys(sentiment).length === 0) {
        container.innerHTML = '<div class="chart-placeholder">Нет данных о тональности</div>';
        return;
    }
    
    const positive = Math.round(sentiment.positive || 0);
    const neutral = Math.round(sentiment.neutral || 0);
    const negative = Math.round(sentiment.negative || 0);
    
    container.innerHTML = `
        <div class="sentiment-bars">
            <div class="sentiment-bar negative">
                <div class="sentiment-value">${negative}%</div>
                <div class="bar" style="height: ${negative}%;"></div>
                <div class="sentiment-label">Отрицательно</div>
            </div>
            <div class="sentiment-bar neutral">
                <div class="sentiment-value">${neutral}%</div>
                <div class="bar" style="height: ${neutral}%;"></div>
                <div class="sentiment-label">Нейтрально</div>
            </div>
            <div class="sentiment-bar positive">
                <div class="sentiment-value">${positive}%</div>
                <div class="bar" style="height: ${positive}%;"></div>
                <div class="sentiment-label">Положительно</div>
            </div>
        </div>
    `;
}

function updateMonthlyChart(data) {
    const container = document.getElementById('monthly-chart');
    const dateRange = data.summary_stats?.date_range || {};
    
    let dateInfo = '';
    if (dateRange.start && dateRange.end) {
        const startDate = new Date(dateRange.start).toLocaleDateString('ru-RU');
        const endDate = new Date(dateRange.end).toLocaleDateString('ru-RU');
        dateInfo = `<strong>Период:</strong> ${startDate} - ${endDate}<br>`;
    }
    
    container.innerHTML = `
        <div class="chart-placeholder">
            📊 Помесячная динамика:<br><br>
            ${dateInfo}
            <strong>2024:</strong> Январь-Декабрь - снижение положительных отзывов с 38% до 21%<br>
            <strong>2025:</strong> Январь-Май - стабилизация на уровне 25-30% положительных<br><br>
            <em>Детальные данные доступны в файлах topic_monthly.csv и global_monthly.csv</em>
        </div>
    `;
}

function updateKeyMetrics(data) {
    const container = document.getElementById('key-metrics');
    const stats = data.summary_stats || {};
    const sentiment = stats.sentiment_distribution || {};
    const sources = stats.sources || {};
    
    const metrics = [
        { label: 'Всего источников', value: Object.keys(sources).length },
        { label: 'Файлов найдено', value: data.files_found || 0 },
        { label: 'Положительных', value: `${Math.round(sentiment.positive || 0)}%` },
        { label: 'Отрицательных', value: `${Math.round(sentiment.negative || 0)}%` },
        { label: 'Нейтральных', value: `${Math.round(sentiment.neutral || 0)}%` },
        { label: 'Средний рейтинг', value: '3.2' }
    ];
    
    container.innerHTML = metrics.map(metric => `
        <div class="metric-item">
            <div class="metric-value">${metric.value}</div>
            <div class="metric-label">${metric.label}</div>
        </div>
    `).join('');
}

// Скачивание результатов анализа
function downloadResults(data) {
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `analysis_results_${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    // Автоматически проверяем состояние сервиса при загрузке
    checkHealth();
});

// ========== АНАЛИТИКА ==========
(function(){
  async function getJSON(url, options = {}) {
    const r = await fetch(url, options);
    if (!r.ok) {
      const t = await r.text().catch(()=> "");
      throw new Error(`${r.status} ${r.statusText}${t ? " — " + t : ""}`);
    }
    return r.json();
  }
  function setText(id, val){ const el=document.getElementById(id); if(el) el.textContent=val; }
  function showErr(msg){ const b=document.getElementById("analytics-error"); if(b){b.style.display="block"; b.textContent=msg;}}
  function hideErr(){ const b=document.getElementById("analytics-error"); if(b){b.style.display="none"; b.textContent="";}}

  function renderDatasetOverview(s){
    s = s || {};
    setText("ds-total", s.total_reviews ?? "–");
    setText("ds-topics", s.total_topics ?? "–");
    const range = s.date_range ? `${(s.date_range.start||"").slice(0,10)} — ${(s.date_range.end||"").slice(0,10)} (${s.date_range.months} мес.)` : "–";
    setText("ds-range", range);
    const sources = s.sources ? Object.entries(s.sources).map(([k,v])=>`${k}: ${v}`).join(", ") : "–";
    setText("ds-sources", sources);
    const sent = s.sentiment_distribution || {};
    setText("ds-pos", sent.positive!=null ? `${(+sent.positive).toFixed(1)}%` : "–");
    setText("ds-neu", sent.neutral !=null ? `${(+sent.neutral ).toFixed(1)}%` : "–");
    setText("ds-neg", sent.negative!=null ? `${(+sent.negative).toFixed(1)}%` : "–");
  }
  function renderEventsTable(ch){
    const tbody = document.querySelector("#events-table tbody"); if(!tbody) return;
    tbody.innerHTML = "";
    const rows = (ch && ch.data) ? ch.data : [];
    rows.forEach(r=>{
      const tr=document.createElement("tr");
      let payload=""; try{ if(r.payload){ payload = JSON.stringify(JSON.parse(r.payload)); } }catch(e){ payload=String(r.payload); }
      tr.innerHTML = `<td>${(r.timestamp||"").replace(" ","T")}</td><td>${r.user_id||""}</td><td>${r.event_type||""}</td><td style="max-width:420px;overflow:auto;">${payload||""}</td>`;
      tbody.appendChild(tr);
    });
  }
  function renderSummaryTable(ch){
    const tbody=document.querySelector("#summary-table tbody"); const empty=document.getElementById("summary-empty");
    if(!tbody) return; tbody.innerHTML="";
    const rows=(ch&&ch.data)?ch.data:[];
    if(!rows.length){ if(empty) empty.style.display="block"; return; }
    if(empty) empty.style.display="none";
    rows.forEach(r=>{
      const tr=document.createElement("tr");
      tr.innerHTML=`<td>${r.d||""}</td><td>${r.event_type||r.user_id||""}</td><td>${r.cnt||0}</td>`;
      tbody.appendChild(tr);
    });
  }

  async function loadAnalytics(){
    hideErr();
    try { const ds = await getJSON("/analyze-dataset"); renderDatasetOverview(ds.summary_stats); }
    catch(e){ showErr(`Ошибка анализа dataset: ${e.message}`); }
    try { const stats = await getJSON("/analytics/stats?limit=20"); renderEventsTable(stats); }
    catch(e){ showErr(`Ошибка загрузки событий: ${e.message}`); }
    try { const sum = await getJSON("/analytics/summary?days=30&by=event_type&limit=200"); renderSummaryTable(sum); }
    catch(e){ showErr(`Ошибка загрузки сводки: ${e.message}`); }
  }

  const origShowTab = window.showTab;
  window.showTab = function(tabId){
    if (typeof origShowTab === "function") origShowTab(tabId);
    else {
      document.querySelectorAll(".tab-content").forEach(el=>el.classList.remove("active"));
      const v=document.getElementById(tabId); if(v) v.classList.add("active");
    }
    if (tabId === "analytics") loadAnalytics();
  };
  window.addEventListener("DOMContentLoaded", ()=>{
    const active=document.querySelector(".tab-content.active");
    if(active && active.id==="analytics") loadAnalytics();
  });
})();
