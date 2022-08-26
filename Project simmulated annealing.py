# -*- coding: utf-8 -*-
"""
Created on Fri Dec 01 19:25:00 2017

@author: Jamil
"""

# -*- coding: utf-8 -*-
"""
Created on Tue Nov 21 11:52:23 2017

@author: Jamil
"""
from pyomo.environ import *
import pandas as pd
import random
import time
infinity = float('inf')

model = ConcreteModel()

#import the excel and their sheets

#Travel Cost
df_travel_cost=pd.read_excel("Travel_information.xlsx", sheetname="Travel_Cost", index_col="Cost")

#Make each city a node
nodes = []
for item in list(df_travel_cost.index):
    nodes.append(item)

#Identify rows and columns
model.row = Set(initialize = set(nodes), name = "row") #df_nodes.index.tolist()
model.col = Set(initialize = set(df_travel_cost.columns.tolist()), name = "col") #df_nodes.columns.tolist()[1:]

def c_init(model, row, col):
    return df_travel_cost[row][col]

model.weights = Param(model.row, model.col, initialize = c_init)

#Set the number of days
days= range(32)
model.duration = Set(initialize = set(days), within=NonNegativeReals)

#Create variable to determine where to travel from and to
model.x=Var(model.row, model.col, model.duration, within=Binary)
model.belgium=Var(within=Binary)
model.iceland=Var(within=Binary)
    
def score(soln):
    row=soln[0]
    col=soln[1]
    duration=[2]
    score = 0
    if duration < 0:
        score += 1000
    score = sum(model.weights[row,col]*model.x[row,col,duration] for row in model.row for col in model.col for duration in model.duration) +\
               sum(35*(model.x[row,"Iceland",duration])+\
               50*(model.x[row,"England",duration])+\
               50*(model.x[row,"France",duration])+\
               45*(model.x[row,"Spain",duration])+\
               40*(model.x[row,"Italy",duration])+\
               40*(model.x[row,"Germany",duration])+\
               35*(model.x[row,"Belgium",duration])\
               for row in  model.row for duration in model.duration)
    return score
print score

def create_neighbor(soln):
    row = soln[0]
    col = soln[1]
    duration = soln [2]
    
    pick=random.randint(0,31)
    
    if row == 1:
        row+=random.uniform(0,7)
    elif col == 1:
        col+= random.uniform(0,7)
    else:
        duration+=random.uniform(0,32)
    
    ###############
    ##Constraints##
    ###############
    
    #Total number of trip
    def tot_duration(model):
        return sum(model.x[row,col,duration] for row in model.row for col in model.col for duration in model.duration) == 32
    model.tot_duration = Constraint(rule=tot_duration)
    
    #Halifax constraints
    def hal_rule(model):
        return sum(model.x["Halifax",col,0] for col in model.col) == 1
    model.hal=Constraint(rule=hal_rule)
    
    def hal_return_rule(model):
            return sum(model.x[row,"Halifax",31] for row in model.row) == 1
    model.hal_return=Constraint(rule=hal_return_rule)
    
    def hal_refrain_rule(model, duration):
        if duration in range(1,30):
            return sum(model.x[row, "Halifax", duration] for row in model.row) == 0
        else:
            return Constraint.Feasible
    model.hal_refrain = Constraint(model.duration, rule=hal_refrain_rule)
    
    #Force visits to each city
    def flow_rule(model, col, duration):
        if duration<31:
            return sum(model.x[row, col, duration] for row in model.row) == sum(model.x[col,row,duration+1] for row in model.row)
        else:
            return Constraint.Feasible
    model.flow = Constraint(model.col, model.duration, rule=flow_rule)
    
    #Must visit each country once and stay at least 3 days
    def country_rule(model, col):
        if col=='Belgium' or col=='Iceland':
           return sum(model.x[row,'Belgium',duration]+model.x[row,'Iceland',duration] for row in model.row for duration in model.duration)==3
        else:
            return sum(model.x[row,col,duration] for row in model.row for duration in model.duration)>=3
    model.country=Constraint(model.col, rule=country_rule)
    
    #England having the last 7 days of the trip
    def eng_rule(model, duration):
        if duration in range(24,30):
            return sum(model.x[row,"England",duration] for row in model.row) == 1
        else:
            return Constraint.Feasible
        if duration < 24 and duration >30:
            return sum(model.x[row,"England",duration] for row in model.row) == 0
        else:
            return Constraint.Feasible
    model.eng_rule = Constraint(model.duration, rule=eng_rule)
    
    #Belgium stay if the student end up travelling to Belgium
    def bel_dur_rule(model, duration):
        if duration in [15,16,17]:
           return sum(model.x[row,'Belgium',duration] for row in model.row) == model.belgium
        else:
            return Constraint.Feasible
    model.bel_dur= Constraint(model.duration, rule = bel_dur_rule)
    
    def belgium_rule(model, row, duration):
        return model.belgium >= model.x[row,'Belgium',duration]
    model.belgium_rule=Constraint(model.row, model.duration, rule=belgium_rule)
    
    def enter_rule(model, col):
         return sum(model.x[row,col,duration] for duration in model.duration for row in model.row if row<>col) <= 1
    model.enter_rule = Constraint(model.col, rule=enter_rule)
        
    return [row,col,duration]

current_soln=[0,0,0]

current_score=score(current_soln)

best_score=score(current_soln) #Initialize best soln score
best_soln=current_soln[:]
Temp=50.0 #For every 10 iterations, Temp=0.5*Temp
print "initial score:", current_score

#Step 3: Iterate
start_time=time.time()

#Stop after 10 second
n=0
while time.time()-start_time<=10:
    #Find a trial solution
    new_soln=create_neighbor(current_soln)
    
    #score new trial solution
    new_score=score(new_soln)
    
    if new_score() < current_score():
        #New score is better
        current_score=new_score
        current_soln=new_soln[:]
        #print "current soln:", current_score
        
        #Check if better than best found so far
        if current_score<best_score:
            print "best found:", new_score
            best_score=new_score
            best_soln=new_soln[:]
    else:
        #New soln is not better
        prob_acceptance=math.exp((current_score-new_score)/Temp)
        
        if random.random()<prob_acceptance:
            #Accept non-improving score
            current_score=new_score
            current_soln=new_soln[:]
            #print "current soln:", current_score

    #Reduce temperature
    if n==10:
        n=0
        Temp=Temp*0.5

print "\nBest solution:", best_soln
print "Best score:", best_score