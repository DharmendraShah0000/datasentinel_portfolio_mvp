import csv, random
random.seed(7)
with open("sample_data/sales_quality_demo.csv","w",newline="") as f:
 w=csv.writer(f);w.writerow(["order_id","region","revenue","units","customer_rating"])
 for i in range(1,501):
  rev=round(random.gauss(180,45),2)
  if i in (45,210,399): rev*=8
  w.writerow([i,random.choice(["North","South","East","West"]),rev,random.randint(1,15),random.choice([1,2,3,4,5,None])])
