type ElsterFieldHintProps = {
  title: string;
  form: string;
  line: string;
  detail: string;
};

function ElsterFieldHint({ title, form, line, detail }: ElsterFieldHintProps) {
  return (
    <aside className="field-hint">
      <div className="field-hint__label">ELSTER field hint</div>
      <h3>{title}</h3>
      <p>
        This value goes into <strong>{form}</strong>, <strong>{line}</strong>.
      </p>
      <span>{detail}</span>
    </aside>
  );
}

export default ElsterFieldHint;
