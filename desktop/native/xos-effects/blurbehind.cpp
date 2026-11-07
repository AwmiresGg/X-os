// SPDX-License-Identifier: BSL-1.0
#include "blurbehind.h"

#include <KWindowEffects>
#include <QPolygon>
#include <QQuickWindow>
#include <QRegion>
#include <QTimer>

BlurBehind::BlurBehind(QObject *parent) : QObject(parent) {}

BlurBehind::~BlurBehind()
{
    if (m_window)
        KWindowEffects::enableBlurBehind(m_window, false);
}

void BlurBehind::setTarget(QQuickItem *t)
{
    if (m_target == t)
        return;
    if (m_target)
        disconnect(m_target, nullptr, this, nullptr);
    m_target = t;
    if (m_target) {
        connect(m_target, &QQuickItem::windowChanged, this, &BlurBehind::schedule);
        connect(m_target, &QQuickItem::xChanged, this, &BlurBehind::schedule);
        connect(m_target, &QQuickItem::yChanged, this, &BlurBehind::schedule);
        connect(m_target, &QQuickItem::widthChanged, this, &BlurBehind::schedule);
        connect(m_target, &QQuickItem::heightChanged, this, &BlurBehind::schedule);
    }
    Q_EMIT changed();
    schedule();
}

void BlurBehind::setEnabled(bool e)
{
    if (m_enabled == e)
        return;
    m_enabled = e;
    Q_EMIT changed();
    schedule();
}

void BlurBehind::setPolygon(const QVariantList &p)
{
    m_polygon = p;
    Q_EMIT changed();
    schedule();
}

// Coalesce updates: the cradle animates every frame, the region only needs the last value.
void BlurBehind::schedule()
{
    if (m_pending)
        return;
    m_pending = true;
    QTimer::singleShot(16, this, [this] { m_pending = false; apply(); });
}

void BlurBehind::apply()
{
    QWindow *w = m_target ? m_target->window() : nullptr;
    if (m_window && m_window != w)
        KWindowEffects::enableBlurBehind(m_window, false);
    m_window = w;
    if (!w)
        return;
    if (!w->isVisible() || !w->handle()) {
        // The platform window does not exist yet; try again once it is shown.
        connect(w, &QWindow::visibleChanged, this, &BlurBehind::schedule, Qt::UniqueConnection);
        return;
    }
    QRegion region;
    if (m_enabled) {
        if (m_polygon.isEmpty()) {
            region = QRegion(m_target->mapRectToScene(QRectF(0, 0, m_target->width(), m_target->height())).toAlignedRect());
        } else {
            QPolygon poly;
            poly.reserve(m_polygon.size());
            for (const QVariant &v : std::as_const(m_polygon)) {
                const QVariantList xy = v.toList();
                if (xy.size() == 2)
                    poly << m_target->mapToScene(QPointF(xy[0].toReal(), xy[1].toReal())).toPoint();
            }
            region = QRegion(poly);
        }
    }
    KWindowEffects::enableBlurBehind(w, m_enabled && !region.isEmpty(), region);
}
