function [thickness_L6b, thickness_L6a, thickness_L5, thickness_L4, thickness_L2and3, thickness_L1]= getThickness (Layer1,Layer2and3,Layer4,Layer5,Layer6a,Layer6b,bottom, m, mOrth,b)
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Finds points of intersection between layer boundaries and orthogonal
% lines
% Returns layer thicknesses
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%


xi= [3873:m:10046];  
 
%linear interpolation of the layers on the interval xi (small step size)
 L1 = interp1(Layer1(:,1),Layer1(:,2),xi ,'linear');
 L2and3 = interp1(Layer2and3(:,1),Layer2and3(:,2),xi ,'linear');
 L4 = interp1(Layer4(:,1),Layer4(:,2),xi ,'linear');
 L5 = interp1(Layer5(:,1),Layer5(:,2),xi ,'linear');
 L6a = interp1(Layer6a(:,1),Layer6a(:,2),xi ,'linear');
 L6b = interp1(Layer6b(:,1),Layer6b(:,2),xi ,'linear');
 Lower = interp1(bottom(:,1),bottom(:,2),xi ,'linear');
 
  
  p= [3873:10*m:10046];
  %the points of intersection with lower boundary (bottom) are known
   for j = 1: length(p)
  if j==1
      CBottom(j,:)= [0 0]; %ignore first element because no corresponding elements in other boundaries
  else
      x(j)= xi(10*(j-1));
      y(j)= Lower(10*(j-1));
      CBottom(j,:)= [y(j) x(j)] ;
  end 
  end
  
  CBottom (1,:)=[];
  
  CL6b =[];
  CL6a =[];
  CL5 =[];
  CL4 =[];
  CL2and3=[];
  CL1= [];
  counters= ones (1,6);
  
  %find intersection with other boundaries
  for j = 1: length(xi)-1
     x= xi(j);
     x2= xi(j+1);
     
     y1L6b= L6b(j);
     y2L6b= L6b(j+1);
     [yL6b,mL6b,bL6b]= lineEQ(x,y1L6b,x2,y2L6b,m); %equation of segment on layer boundary
     CoordL6b = getIntersection (-mOrth, -mL6b, bL6b, b); %intersection between segment and perpendicular line
     for k=1:length(b)
     if CoordL6b (k,2)<x | CoordL6b (k,2)>x2 %if intersection is outside segment, ignore
         CoordL6b (k,:)=[0 0];
     end
     end
     minus = find (CoordL6b(:,2)==0);
     CoordL6b(minus,:)=[];
     
     if ~isempty (CoordL6b)
         
     CL6b(counters(1,6),:)= CoordL6b; %store points of intersection
     counters(1,6)=counters(1,6)+1;
     end
     
     y1L6a=L6a(j);
     y2L6a=L6a(j+1);
     [yL6a,mL6a,bL6a]= lineEQ(x,y1L6a,x2,y2L6a,m);
      CoordL6a =getIntersection (-mOrth, -mL6a, bL6a, b);
      for k=1:length(b)
     if CoordL6a (k,2)<x | CoordL6a (k,2)>x2
         CoordL6a (k,:)=[0 0];
     end
      end
      minus = find (CoordL6a==0);
     CoordL6a(minus)=[];
     if ~isempty (CoordL6a)
         CL6a(counters(1,5),:)= CoordL6a;
     counters(1,5)=counters(1,5)+1;
     
     end
     
     y1L5=L5(j);
     y2L5=L5(j+1);
     [yL5,mL5,bL5]= lineEQ(x,y1L5,x2,y2L5,m);
     CoordL5 =getIntersection (-mOrth, -mL5, bL5, b);
     for k=1:length(b)
     if CoordL5 (k,2)<x | CoordL5 (k,2)>x2
         CoordL5 (k,:)=[0 0];
     end
     end
     minus = find (CoordL5==0);
     CoordL5(minus)=[];
     if ~isempty (CoordL5)
      CL5(counters(1,4),:)= CoordL5;
     counters(1,4)=counters(1,4)+1;
     end
     
     y1L4=L4(j);
     y2L4=L4(j+1);
     [yL4,mL4,bL4]= lineEQ(x,y1L4,x2,y2L4,m);
     CoordL4 =getIntersection (-mOrth, -mL4, bL4, b);
     for k=1:length(b)
         if CoordL4 (k,2)<x | CoordL4 (k,2)>x2
         CoordL4 (k,:)=[0 0];
        end
     end
     minus = find (CoordL4==0);
    CoordL4(minus)=[];
    if ~isempty (CoordL4)
        CL4(counters(1,3),:)= CoordL4;
     counters(1,3)=counters(1,3)+1;
      end
    
         y1L2and3=L2and3(j);
     y2L2and3=L2and3(j+1);
     [yL2and3,mL2and3,bL2and3]= lineEQ(x,y1L2and3,x2,y2L2and3,m);
     CoordL2and3 = getIntersection (-mOrth, -mL2and3, bL2and3, b);
     for k=1:length(b)
     if CoordL2and3 (k,2)<x | CoordL2and3 (k,2)>x2
         CoordL2and3 (k,:)=[0 0];
     end
     end
     minus = find (CoordL2and3==0);
     CoordL2and3(minus)=[];
     if ~isempty (CoordL2and3)
         CL2and3(counters(1,2),:)= CoordL2and3;
     counters(1,2)=counters(1,2)+1;
     
     end
     
     y1L1=L1(j);
     y2L1=L1(j+1);
     [yL1,mL1,bL1]= lineEQ(x,y1L1,x2,y2L1,m);
     CoordL1 = getIntersection (-mOrth, -mL1, bL1, b);
     for k=1:length(b)
     if CoordL1 (k,2)<x | CoordL1 (k,2)>x2
         CoordL1 (k,:)=[0 0];
     end
     end     
     minus = find (CoordL1==0);
     CoordL1(minus)=[];
     if ~isempty (CoordL1)
         CL1(counters(1,1),:)= CoordL1;
     counters(1,1)=counters(1,1)+1;
     
     end
  end
  

 %calculate thicknesses as the distance between two points of intersection
for z= 1:length (CL6a)
    thickness_L1(z)= sqrt((CL2and3(z,1)-CL1(z,1))^2 + (CL2and3(z,2) - CL1(z,2))^2);
    thickness_L2and3(z)= sqrt((CL4(z,1)-CL2and3(z,1))^2 +(CL4(z,2)-CL2and3(z,2))^2);
    thickness_L4(z)= sqrt((CL5(z,1)-CL4(z,1))^2 +(CL5(z,2)-CL4(z,2))^2);
    thickness_L5(z)= sqrt((CL6a(z,1)-CL5(z,1))^2 + (CL6a(z,2)-CL5(z,2))^2);
    thickness_L6a(z)= sqrt((CL6b(z,1)-CL6a(z,1))^2 + (CL6b(z,2)-CL6a(z,2))^2);
    thickness_L6b(z)= sqrt((CBottom(z,1)-CL6b(z,1))^2 + (CBottom(z,2)-CL6b(z,2))^2);
end  
  
  