# -*- coding: utf-8 -*-
"""
Created on Tue Nov 21 11:52:23 2017

@author: Jamil
"""
from pyomo.environ import *
import pandas as pd

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

#1 if going to Belgium
model.belgium=Var(within=Binary)
model.iceland=Var(within=Binary)

######################
##Objective Function##
######################

def cost_rule(model):
    return sum(model.weights[row,col]*model.x[row,col,duration] for row in model.row for col in model.col for duration in model.duration) +\
               sum(35*(model.x[row,"Iceland",duration])+\
               50*(model.x[row,"England",duration])+\
               50*(model.x[row,"France",duration])+\
               45*(model.x[row,"Spain",duration])+\
               40*(model.x[row,"Italy",duration])+\
               40*(model.x[row,"Germany",duration])+\
               35*(model.x[row,"Belgium",duration])\
               for row in  model.row for duration in model.duration)
model.cost = Objective(rule = cost_rule)

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
        
#########
##Solve##
#########

model.preprocess()
opt = SolverFactory('glpk')

results=opt.solve(model, symbolic_solver_labels=True, tee=True)

#############
##Reporting##
#############

print model.cost()

for duration in model.duration:
    for row in model.row:
        for col in model.col:
            if model.x[row,col,duration].value>0:
                print row,col,duration, model.x[row,col,duration].value