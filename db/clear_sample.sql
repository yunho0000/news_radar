-- 샘플 데이터만 지운다 (실제 데이터는 그대로 둔다).
-- 실행: SQL Editor에 붙여넣기 → Run
-- 수집 회차 기록·성과는 소재·게시물을 지우면 함께 지워진다.

delete from events       where memo = '샘플';
delete from watchlist    where memo = '샘플';
delete from posts        where title like '[샘플]%';
delete from topics       where memo = '샘플 데이터';
