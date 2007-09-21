function [y,m,b]= lineEQ(x1,y1,x2,y2,m)
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% given coordinates of two points, it returns the equation of the line joining those two points
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
x= [3873:m:10046];

syms y 
m= (y2-y1)/(x2-x1); %slope
b=y1-m*x1;

y= m*x+b;



