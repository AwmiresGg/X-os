// SPDX-License-Identifier: BSL-1.0
#pragma once
#include <QObject>
#include <QPointer>
#include <QQuickItem>
#include <QVariantList>
#include <QtQml/qqmlregistration.h>

// Requests compositor blur behind `target`, limited to `polygon` (target-local [x, y] points;
// empty = the target's bounding rectangle). No-op where the compositor has no blur.
class BlurBehind : public QObject
{
    Q_OBJECT
    QML_ELEMENT
    Q_PROPERTY(QQuickItem *target READ target WRITE setTarget NOTIFY changed)
    Q_PROPERTY(bool enabled READ enabled WRITE setEnabled NOTIFY changed)
    Q_PROPERTY(QVariantList polygon READ polygon WRITE setPolygon NOTIFY changed)

public:
    explicit BlurBehind(QObject *parent = nullptr);
    ~BlurBehind() override;

    QQuickItem *target() const { return m_target; }
    void setTarget(QQuickItem *t);
    bool enabled() const { return m_enabled; }
    void setEnabled(bool e);
    QVariantList polygon() const { return m_polygon; }
    void setPolygon(const QVariantList &p);

Q_SIGNALS:
    void changed();

private:
    void schedule();
    void apply();
    QPointer<QQuickItem> m_target;
    QPointer<QWindow> m_window;
    bool m_enabled = true;
    bool m_pending = false;
    QVariantList m_polygon;
};
