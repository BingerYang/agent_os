import { useEffect, useState } from 'react'
import { Checkbox, Input, InputNumber, Select, Space, Switch, Tag } from 'antd'
import { detectionRuleApi } from '../api'

interface SchemaField {
  type: string
  label: string
  default?: unknown
  options?: string[]
}

interface ConfigSchema {
  [field: string]: SchemaField
}

interface StrategyMeta {
  value: string
  label: string
  config_schema: ConfigSchema
}

interface Props {
  strategyType: string
  value?: Record<string, unknown>
  onChange?: (val: Record<string, unknown>) => void
  configSchema?: ConfigSchema
  disabled?: boolean
}

export default function DetectionStrategyForm({
  strategyType,
  value = {},
  onChange,
  configSchema: externalSchema,
  disabled = false,
}: Props) {
  const [schema, setSchema] = useState<ConfigSchema | null>(externalSchema ?? null)

  useEffect(() => {
    if (externalSchema) {
      setSchema(externalSchema)
      return
    }
    if (!strategyType) return
    detectionRuleApi.meta().then((data: unknown) => {
      const meta = data as { strategy_types: StrategyMeta[] }
      const found = meta.strategy_types.find((s) => s.value === strategyType)
      setSchema(found?.config_schema ?? null)
    }).catch(() => setSchema(null))
  }, [strategyType, externalSchema])

  const set = (key: string, val: unknown) => {
    onChange?.({ ...value, [key]: val })
  }

  if (!schema) {
    return (
      <Input.TextArea
        rows={6}
        value={JSON.stringify(value, null, 2)}
        disabled={disabled}
        onChange={(e) => {
          try { onChange?.(JSON.parse(e.target.value)) } catch { /* ignore */ }
        }}
        placeholder={`{"key": "value"}`}
        className="mono-textarea"
      />
    )
  }

  return (
    <Space direction="vertical" style={{ width: '100%' }} size={12}>
      {Object.entries(schema).map(([key, field]) => {
        const current = key in value ? value[key] : field.default
        return (
          <div key={key}>
            <div style={{ marginBottom: 4, fontSize: 13, color: '#595959' }}>{field.label}</div>
            {field.type === 'integer' || field.type === 'number' ? (
              <InputNumber
                value={current as number}
                onChange={(v) => set(key, v)}
                disabled={disabled}
                style={{ width: '100%' }}
                step={field.type === 'number' ? 0.01 : 1}
              />
            ) : field.type === 'boolean' ? (
              <Switch
                checked={current as boolean}
                onChange={(v) => set(key, v)}
                disabled={disabled}
                checkedChildren="是"
                unCheckedChildren="否"
              />
            ) : field.type === 'select' ? (
              <Select
                value={current as string}
                onChange={(v) => set(key, v)}
                disabled={disabled}
                style={{ width: '100%' }}
                options={(field.options ?? []).map((o) => ({ label: o, value: o }))}
              />
            ) : field.type === 'multiselect' ? (
              <Checkbox.Group
                value={current as string[]}
                onChange={(v) => set(key, v)}
                disabled={disabled}
                options={(field.options ?? []).map((o) => ({ label: o, value: o }))}
              />
            ) : field.type === 'stringlist' ? (
              <StringListInput
                value={current as string[]}
                onChange={(v) => set(key, v)}
                disabled={disabled}
              />
            ) : field.type === 'textarea' ? (
              <Input.TextArea
                value={current as string}
                onChange={(e) => set(key, e.target.value)}
                disabled={disabled}
                rows={4}
                className="mono-textarea"
              />
            ) : (
              <Input
                value={current as string}
                onChange={(e) => set(key, e.target.value)}
                disabled={disabled}
              />
            )}
          </div>
        )
      })}
    </Space>
  )
}

function StringListInput({
  value = [],
  onChange,
  disabled,
}: {
  value?: string[]
  onChange?: (v: string[]) => void
  disabled?: boolean
}) {
  const [input, setInput] = useState('')
  const add = () => {
    const trimmed = input.trim()
    if (trimmed && !value.includes(trimmed)) {
      onChange?.([...value, trimmed])
      setInput('')
    }
  }
  return (
    <Space direction="vertical" style={{ width: '100%' }}>
      <Space wrap>
        {value.map((v) => (
          <Tag
            key={v}
            closable={!disabled}
            onClose={() => onChange?.(value.filter((x) => x !== v))}
          >
            {v}
          </Tag>
        ))}
      </Space>
      {!disabled && (
        <Input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onPressEnter={add}
          placeholder="输入后按 Enter 添加"
          style={{ width: 220 }}
        />
      )}
    </Space>
  )
}
