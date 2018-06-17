# lp-workout-manager
Tool to track weights for a standard linear progression workout. Utilizes Jupyter Notebook as the fronted, and `sqlite` as the backend database. This inputs of this tool are specific to a 5-3-1 workout with four 4x10 accessory exercises for each split.

### Features
* Merges a `mapping_dictionary` onto user defined `one_rep_max` weights to generate a complete workout
* Stores accessory exercises to correpond to each main exercise
* Creates a reference document for how much weight to put on each side of the bar (45lb bar assumed)
* Packages all information into a nice html document

### Database Schema
```python
with con:
    cur = con.cursor() 
    cur.execute("CREATE TABLE dim_user(user_id INT, user_name STRING, email STRING)")
    cur.execute("CREATE TABLE dim_progression(user_id INT, prog_dict JSON)")
    cur.execute("CREATE TABLE one_rep_max(user_id INT, data_start_date TIMESTAMP, data_end_date TIMESTAMP, orm_dict JSON, publish_time TIMESTAMP)")
    cur.execute("CREATE TABLE accessory(user_id INT, me_name STRING, ae_name STRING, ae_weight FLOAT, sets INT, reps INT, publish_time TIMESTAMP)")
    cur.execute("CREATE TABLE pause_workout(user_id INT, pause_date TIMESTAMP DEFAULT '2999-12-31 23:59:59', pause_flag BOOLEAN DEFAULT False)")
```

