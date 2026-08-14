const Table = ({ columns, children }) => (
  <div className="overflow-x-auto rounded-2xl border border-[#DEE7F1] bg-white shadow-[0_18px_46px_-34px_rgba(15,27,45,.4)]">
    <table className="min-w-full divide-y divide-[#EEF2F7] text-xs">
      <thead className="bg-[#F7FAFD]">
        <tr>
          {columns.map((col) => (
            <th
              key={col}
              className="px-3 py-2.5 text-center text-[10px] font-extrabold uppercase leading-tight tracking-[.06em] text-[#8494A9]"
            >
              <span className="mx-auto block max-w-[110px]">{col}</span>
            </th>
          ))}
        </tr>
      </thead>
      <tbody className="divide-y divide-[#EEF2F7] bg-white text-center text-[#41536B]">{children}</tbody>
    </table>
  </div>
);

export default Table;
